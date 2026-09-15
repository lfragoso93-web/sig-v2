"""Dry-run read-only para reconciliacao de eventos corporativos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventEvidence,
    CorporateEventReconciliationDecision,
    CorporateEventReconciliationDryRunReport,
    build_reconciliation_dry_run_report,
)


def evidence_from_event(event: CorporateEvent) -> CorporateEventEvidence:
    return CorporateEventEvidence(
        event_id=int(event.id),
        ticker=str(event.ticker),
        event_type=str(event.event_type),
        source_provider=str(event.source_provider),
        source_event_id=event.source_event_id,
    )


async def build_corporate_event_reconciliation_dry_run(
    db: AsyncSession,
    *,
    event_ids: tuple[int, ...],
    decision: CorporateEventReconciliationDecision,
    reason: str,
    canonical_event_id: int | None = None,
) -> CorporateEventReconciliationDryRunReport:
    if not event_ids:
        raise ValueError("event_ids e obrigatorio")
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("event_ids contem duplicidade")

    result = await db.execute(
        select(CorporateEvent).where(CorporateEvent.id.in_(event_ids))
    )
    events = tuple(sorted(result.scalars().all(), key=lambda item: int(item.id)))
    found_ids = {int(event.id) for event in events}
    missing = sorted(set(event_ids) - found_ids)
    if missing:
        raise ValueError(f"eventos nao encontrados: {missing}")

    return build_reconciliation_dry_run_report(
        tuple(evidence_from_event(event) for event in events),
        decision=decision,
        reason=reason,
        canonical_event_id=canonical_event_id,
    )
