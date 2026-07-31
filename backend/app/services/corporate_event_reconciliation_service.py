"""Reconciliação determinística do catálogo global de eventos corporativos."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import (
    CorporateEvent,
    CorporateEventReconciliationStatus,
    CorporateEventStatus,
    CorporateEventType,
)

_SOURCE_PRIORITY = {"brapi": 0, "manual": 1, "yahoo": 2, "legacy": 50}
_SAFE_MATCHED_TYPES = {
    CorporateEventType.DESDOBRAMENTO.value,
    CorporateEventType.GRUPAMENTO.value,
    CorporateEventType.BONIFICACAO.value,
    CorporateEventType.TICKER_CHANGE.value,
}


@dataclass(frozen=True)
class CorporateEventReconciliationReport:
    total: int
    matched: int
    conflicts: int
    unreconciled: int
    canonical: int
    suppressed_equivalents: int


def _hash(value: dict[str, object]) -> str:
    serialized = json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _effective_date(event: CorporateEvent) -> date:
    value = event.effective_date or event.event_date
    if value is None:
        raise ValueError(f"evento corporativo {event.id} sem data efetiva")
    return value


def _factor(event: CorporateEvent) -> Decimal:
    value = event.quantity_factor if event.quantity_factor is not None else event.ratio
    if value is None:
        raise ValueError(f"evento corporativo {event.id} sem fator")
    return Decimal(str(value))


def _event_type(event: CorporateEvent) -> str:
    value = event.event_type
    return str(getattr(value, "value", value))


def _group_hash(event: CorporateEvent) -> str:
    return _hash(
        {
            "asset_id": event.asset_id,
            "ticker": str(event.ticker).upper(),
            "event_type": _event_type(event),
            "effective_date": _effective_date(event).isoformat(),
            "destination_asset_id": event.destination_asset_id,
            "destination_ticker": str(event.destination_ticker or "").upper() or None,
        }
    )


def _economic_hash(event: CorporateEvent) -> str:
    return _hash(
        {
            "group": _group_hash(event),
            "quantity_factor": str(_factor(event)),
            "cash_component": str(event.cash_component or ""),
            "subscription_price": str(event.subscription_price or ""),
        }
    )


def _canonical_event(events: Iterable[CorporateEvent]) -> CorporateEvent:
    return min(
        events,
        key=lambda event: (
            _SOURCE_PRIORITY.get(str(event.source_provider).lower(), 99),
            str(event.source_provider),
            str(event.source_event_id or ""),
            event.id or 0,
        ),
    )


def reconcile_corporate_event_records(
    events: Iterable[CorporateEvent],
    *,
    reconciled_at: datetime | None = None,
) -> CorporateEventReconciliationReport:
    """Reconcilia objetos carregados sem confirmar transação ou aplicar efeitos."""
    rows = list(events)
    now = reconciled_at or datetime.now(UTC)
    groups: dict[str, list[CorporateEvent]] = defaultdict(list)
    for event in rows:
        manually_reviewed = (
            event.reviewed_by_user_id is not None
            and event.reviewed_at is not None
            and event.status
            in {
                CorporateEventStatus.VALIDATED.value,
                CorporateEventStatus.REJECTED.value,
            }
        )
        if manually_reviewed:
            continue
        event.reconciliation_group_hash = _group_hash(event)
        event.economic_identity_hash = _economic_hash(event)
        groups[event.reconciliation_group_hash].append(event)

    matched = conflicts = unreconciled = canonical_count = suppressed = 0
    for group in groups.values():
        economic_groups: dict[str, list[CorporateEvent]] = defaultdict(list)
        for event in group:
            economic_groups[event.economic_identity_hash].append(event)

        distinct_sources = {str(event.source_provider).lower() for event in group}
        if len(economic_groups) > 1 and len(distinct_sources) > 1:
            conflicts += len(group)
            for event in group:
                event.reconciliation_status = (
                    CorporateEventReconciliationStatus.CONFLICT.value
                )
                event.requires_review = True
                event.review_reason = (
                    "fontes divergem para o mesmo tipo, ativo e data efetiva"
                )
                event.is_canonical = False
                event.matched_event_id = None
                event.reconciled_at = now
            continue

        if len(group) == 1 or len(distinct_sources) == 1:
            unreconciled += len(group)
            for event in group:
                event.reconciliation_status = (
                    CorporateEventReconciliationStatus.UNRECONCILED.value
                )
                event.requires_review = True
                event.review_reason = (
                    "evento ainda sem confirmação por fonte independente"
                )
                event.is_canonical = True
                event.matched_event_id = None
                event.reconciled_at = now
                canonical_count += 1
            continue

        canonical = _canonical_event(group)
        safe = _event_type(canonical) in _SAFE_MATCHED_TYPES
        for event in group:
            event.reconciliation_status = (
                CorporateEventReconciliationStatus.MATCHED.value
            )
            event.requires_review = not safe
            event.review_reason = (
                None if safe else "tipo exige revisão mesmo com fontes concordantes"
            )
            event.is_canonical = event is canonical
            event.matched_event_id = None if event is canonical else canonical.id
            event.reconciled_at = now
            if event is canonical:
                canonical_count += 1
                if safe:
                    event.status = CorporateEventStatus.VALIDATED.value
            else:
                suppressed += 1
        matched += len(group)

    return CorporateEventReconciliationReport(
        total=len(rows),
        matched=matched,
        conflicts=conflicts,
        unreconciled=unreconciled,
        canonical=canonical_count,
        suppressed_equivalents=suppressed,
    )


async def reconcile_corporate_events_for_asset(
    db: AsyncSession, asset_id: int
) -> CorporateEventReconciliationReport:
    """Reconcilia o catálogo global de um ativo; o chamador controla commit."""
    await db.flush()
    result = await db.execute(
        select(CorporateEvent)
        .where(
            CorporateEvent.asset_id == asset_id,
            CorporateEvent.portfolio_id.is_(None),
        )
        .order_by(CorporateEvent.effective_date, CorporateEvent.id)
    )
    report = reconcile_corporate_event_records(result.scalars().all())
    await db.flush()
    return report
