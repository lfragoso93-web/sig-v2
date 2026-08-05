"""Classificação read-only para a futura contração do legado corporativo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent


class LegacyCorporateEventDisposition(str, Enum):
    RECONCILABLE = "reconcilable"
    INCOMPLETE = "incomplete"
    BLOCKED_REVIEW = "blocked_review"


@dataclass(frozen=True)
class LegacyCorporateEventClassification:
    event_id: int
    disposition: LegacyCorporateEventDisposition
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        return payload


@dataclass(frozen=True)
class LegacyCorporateEventDryRun:
    total: int
    reconcilable: int
    incomplete: int
    blocked_review: int
    samples: tuple[LegacyCorporateEventClassification, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "reconcilable": self.reconcilable,
            "incomplete": self.incomplete,
            "blocked_review": self.blocked_review,
            "samples": [item.to_dict() for item in self.samples],
        }


def classify_legacy_corporate_event(
    event: CorporateEvent,
) -> LegacyCorporateEventClassification:
    """Classifica uma linha sem alterar ou inferir dados ausentes."""

    missing: list[str] = []
    if not str(event.ticker or "").strip():
        missing.append("ticker")
    if not str(event.event_type or "").strip():
        missing.append("event_type")
    if not str(event.source_event_id or "").strip():
        missing.append("source_event_id")
    if event.effective_date is None:
        missing.append("effective_date")
    if event.quantity_factor is None:
        missing.append("quantity_factor")

    if missing:
        return LegacyCorporateEventClassification(
            event_id=int(event.id),
            disposition=LegacyCorporateEventDisposition.INCOMPLETE,
            reasons=tuple(f"missing:{field}" for field in missing),
        )

    blocked: list[str] = []
    if event.portfolio_id is not None:
        blocked.append("portfolio_bound")
    if str(event.status or "").strip().upper() == "IGNORADO":
        blocked.append("ignored")

    if blocked:
        return LegacyCorporateEventClassification(
            event_id=int(event.id),
            disposition=LegacyCorporateEventDisposition.BLOCKED_REVIEW,
            reasons=tuple(blocked),
        )

    return LegacyCorporateEventClassification(
        event_id=int(event.id),
        disposition=LegacyCorporateEventDisposition.RECONCILABLE,
        reasons=("canonical_fields_complete",),
    )


async def build_legacy_corporate_event_dry_run(
    db: AsyncSession,
    *,
    sample_limit: int = 20,
) -> LegacyCorporateEventDryRun:
    """Produz uma prévia determinística sem executar backfill ou reconciliação."""

    provider = func.lower(func.coalesce(CorporateEvent.source_provider, ""))
    result = await db.execute(
        select(CorporateEvent)
        .where(provider.in_(["", "legacy"]))
        .order_by(CorporateEvent.id)
    )
    classifications = [
        classify_legacy_corporate_event(event)
        for event in result.scalars().all()
    ]

    counts = {
        disposition: sum(
            item.disposition is disposition for item in classifications
        )
        for disposition in LegacyCorporateEventDisposition
    }

    safe_limit = max(0, int(sample_limit))
    return LegacyCorporateEventDryRun(
        total=len(classifications),
        reconcilable=counts[LegacyCorporateEventDisposition.RECONCILABLE],
        incomplete=counts[LegacyCorporateEventDisposition.INCOMPLETE],
        blocked_review=counts[LegacyCorporateEventDisposition.BLOCKED_REVIEW],
        samples=tuple(classifications[:safe_limit]),
    )
