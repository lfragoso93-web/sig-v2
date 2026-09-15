"""Dry-run read-only para reconciliacao de eventos corporativos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventEvidence,
    CorporateEventMatchResolutionEvidence,
    CorporateEventReconciliationDecision,
    CorporateEventReconciliationDryRunReport,
    CorporateEventReconciliationUpdate,
    build_reconciliation_execution_report,
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
    match_resolution_evidence: CorporateEventMatchResolutionEvidence | None = None,
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
        match_resolution_evidence=match_resolution_evidence,
    )


def _apply_update(event: CorporateEvent, update: CorporateEventReconciliationUpdate) -> None:
    event.reconciliation_status = update.reconciliation_status
    event.requires_review = update.requires_review
    event.is_canonical = update.is_canonical
    event.matched_event_id = update.matched_event_id
    event.review_reason = update.review_reason


async def execute_corporate_event_conflict_reconciliation(
    db: AsyncSession,
    *,
    event_ids: tuple[int, ...],
    reason: str,
) -> CorporateEventReconciliationDryRunReport:
    report = await build_corporate_event_reconciliation_dry_run(
        db,
        event_ids=event_ids,
        decision=CorporateEventReconciliationDecision.CONFLICT,
        reason=reason,
    )
    result = await db.execute(
        select(CorporateEvent)
        .where(CorporateEvent.id.in_(event_ids))
        .with_for_update()
    )
    events_by_id = {int(event.id): event for event in result.scalars().all()}
    for update in report.updates:
        event = events_by_id.get(update.event_id)
        if event is None:
            raise ValueError(f"evento nao encontrado durante execucao: {update.event_id}")
        _apply_update(event, update)
    await db.flush()
    return build_reconciliation_execution_report(
        report.updates,
        decision=CorporateEventReconciliationDecision.CONFLICT,
        database_writes_executed=len(report.updates),
    )
