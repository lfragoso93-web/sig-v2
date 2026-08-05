"""Plano read-only para futura contração do legado de eventos corporativos."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.services.corporate_event_legacy_dry_run_service import (
    LegacyCorporateEventDisposition,
    classify_legacy_corporate_event,
)


class LegacyBackfillAction(str, Enum):
    RECONCILE_ONLY = "reconcile_only"
    BACKFILL_CANDIDATE = "backfill_candidate"
    MANUAL_REVIEW = "manual_review"
    BLOCKED_REVIEW = "blocked_review"


@dataclass(frozen=True)
class LegacyBackfillPlanEntry:
    event_id: int
    action: LegacyBackfillAction
    proposed_updates: dict[str, object]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


@dataclass(frozen=True)
class LegacyBackfillPlan:
    total: int
    reconcile_only: int
    backfill_candidate: int
    manual_review: int
    blocked_review: int
    entries: tuple[LegacyBackfillPlanEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "reconcile_only": self.reconcile_only,
            "backfill_candidate": self.backfill_candidate,
            "manual_review": self.manual_review,
            "blocked_review": self.blocked_review,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _serialized_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def plan_legacy_corporate_event_backfill(
    event: CorporateEvent,
) -> LegacyBackfillPlanEntry:
    """Descreve mudanças deriváveis sem executar qualquer mutação."""

    classification = classify_legacy_corporate_event(event)
    if classification.disposition is LegacyCorporateEventDisposition.BLOCKED_REVIEW:
        return LegacyBackfillPlanEntry(
            event_id=int(event.id),
            action=LegacyBackfillAction.BLOCKED_REVIEW,
            proposed_updates={},
            blockers=classification.reasons,
        )

    proposed_updates: dict[str, object] = {}
    blockers: list[str] = []

    if not str(event.source_event_id or "").strip():
        legacy_identity = str(event.brapi_event_id or "").strip()
        proposed_updates["source_event_id"] = legacy_identity or f"legacy:{event.id}"

    if event.effective_date is None:
        if event.event_date is None:
            blockers.append("missing:event_date")
        else:
            proposed_updates["effective_date"] = _serialized_value(event.event_date)

    if event.quantity_factor is None:
        if event.ratio is None:
            blockers.append("missing:ratio")
        else:
            proposed_updates["quantity_factor"] = _serialized_value(event.ratio)

    if not str(event.ticker or "").strip():
        blockers.append("missing:ticker")
    if not str(event.event_type or "").strip():
        blockers.append("missing:event_type")

    if blockers:
        return LegacyBackfillPlanEntry(
            event_id=int(event.id),
            action=LegacyBackfillAction.MANUAL_REVIEW,
            proposed_updates=proposed_updates,
            blockers=tuple(blockers),
        )

    if proposed_updates:
        return LegacyBackfillPlanEntry(
            event_id=int(event.id),
            action=LegacyBackfillAction.BACKFILL_CANDIDATE,
            proposed_updates=proposed_updates,
            blockers=(),
        )

    return LegacyBackfillPlanEntry(
        event_id=int(event.id),
        action=LegacyBackfillAction.RECONCILE_ONLY,
        proposed_updates={},
        blockers=(),
    )


async def build_legacy_corporate_event_backfill_plan(
    db: AsyncSession,
    *,
    entry_limit: int = 100,
) -> LegacyBackfillPlan:
    """Gera artefato determinístico sem UPDATE, commit ou acesso a providers."""

    provider = func.lower(func.coalesce(CorporateEvent.source_provider, ""))
    result = await db.execute(
        select(CorporateEvent)
        .where(provider.in_(["", "legacy"]))
        .order_by(CorporateEvent.id)
    )
    entries = [
        plan_legacy_corporate_event_backfill(event)
        for event in result.scalars().all()
    ]
    counts = {
        action: sum(entry.action is action for entry in entries)
        for action in LegacyBackfillAction
    }
    safe_limit = max(0, int(entry_limit))

    return LegacyBackfillPlan(
        total=len(entries),
        reconcile_only=counts[LegacyBackfillAction.RECONCILE_ONLY],
        backfill_candidate=counts[LegacyBackfillAction.BACKFILL_CANDIDATE],
        manual_review=counts[LegacyBackfillAction.MANUAL_REVIEW],
        blocked_review=counts[LegacyBackfillAction.BLOCKED_REVIEW],
        entries=tuple(entries[:safe_limit]),
    )
