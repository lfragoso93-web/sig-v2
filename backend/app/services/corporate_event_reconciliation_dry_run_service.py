"""Dry-run read-only para reconciliacao de eventos corporativos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.models.corporate_event_reconciliation_evidence import (
    CorporateEventReconciliationEvidence,
)
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventEvidence,
    CorporateEventMatchResolutionEvidence,
    CorporateEventReconciliationDecision,
    CorporateEventReconciliationDryRunReport,
    CorporateEventReconciliationUpdate,
    build_reconciliation_execution_report,
    build_reconciliation_dry_run_report,
)
from app.services.corporate_event_ledger_preflight import (
    build_corporate_event_ledger_preflight_report,
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
    ledger_preflight_event_id: int | None = None,
    ledger_preflight_portfolio_id: int | None = None,
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

    report = build_reconciliation_dry_run_report(
        tuple(evidence_from_event(event) for event in events),
        decision=decision,
        reason=reason,
        canonical_event_id=canonical_event_id,
        match_resolution_evidence=match_resolution_evidence,
    )
    if ledger_preflight_event_id is None:
        return report
    event_by_id = {int(event.id): event for event in events}
    ledger_event = event_by_id.get(ledger_preflight_event_id)
    if ledger_event is None:
        raise ValueError(
            "ledger_preflight_event_id deve pertencer aos event_ids"
        )
    ledger_report = await build_corporate_event_ledger_preflight_report(
        db,
        ledger_event,
        portfolio_id=ledger_preflight_portfolio_id,
    )
    return CorporateEventReconciliationDryRunReport(
        schema_version=report.schema_version,
        ok=report.ok,
        decision=report.decision,
        dry_run=report.dry_run,
        database_writes_executed=report.database_writes_executed,
        event_ids=report.event_ids,
        updates=report.updates,
        match_resolution_evidence=report.match_resolution_evidence,
        ledger_preflight=ledger_report.to_dict(),
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


async def execute_corporate_event_matched_reconciliation(
    db: AsyncSession,
    *,
    event_ids: tuple[int, ...],
    canonical_event_id: int,
    reason: str,
    match_resolution_evidence: CorporateEventMatchResolutionEvidence,
) -> CorporateEventReconciliationDryRunReport:
    """Persiste MATCHED + evidencia sem assumir commit da transacao."""

    if not event_ids:
        raise ValueError("event_ids e obrigatorio")
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("event_ids contem duplicidade")

    result = await db.execute(
        select(CorporateEvent)
        .where(CorporateEvent.id.in_(event_ids))
        .order_by(CorporateEvent.id)
        .with_for_update()
    )
    events = tuple(
        sorted(result.scalars().all(), key=lambda item: int(item.id))
    )

    events_by_id = {int(event.id): event for event in events}
    found_ids = set(events_by_id)
    requested_ids = set(event_ids)
    missing = sorted(requested_ids - found_ids)

    if missing:
        raise ValueError(
            f"eventos nao encontrados durante execucao: {missing}"
        )

    contract_report = build_reconciliation_dry_run_report(
        tuple(evidence_from_event(event) for event in events),
        decision=CorporateEventReconciliationDecision.MATCHED,
        canonical_event_id=canonical_event_id,
        reason=reason,
        match_resolution_evidence=match_resolution_evidence,
    )
    updates = contract_report.updates

    existing_result = await db.execute(
        select(CorporateEventReconciliationEvidence)
        .where(
            CorporateEventReconciliationEvidence.corporate_event_id
            == canonical_event_id
        )
        .with_for_update()
    )
    existing = existing_result.scalar_one_or_none()

    expected = {
        "decision": CorporateEventReconciliationDecision.MATCHED.value,
        "evidence_type": match_resolution_evidence.evidence_type.value,
        "evidence_reference": match_resolution_evidence.evidence_reference,
        "fractional_policy": match_resolution_evidence.fractional_policy.value,
        "fractional_quantity": match_resolution_evidence.fractional_quantity,
        "fractional_settlement_price": (
            match_resolution_evidence.fractional_settlement_price
        ),
        "cash_treatment": match_resolution_evidence.cash_treatment,
    }

    if existing is None:
        db.add(
            CorporateEventReconciliationEvidence(
                corporate_event_id=canonical_event_id,
                **expected,
            )
        )
        evidence_write_count = 1
    else:
        actual = {
            "decision": existing.decision,
            "evidence_type": existing.evidence_type,
            "evidence_reference": existing.evidence_reference,
            "fractional_policy": existing.fractional_policy,
            "fractional_quantity": existing.fractional_quantity,
            "fractional_settlement_price": (
                existing.fractional_settlement_price
            ),
            "cash_treatment": existing.cash_treatment,
        }

        if actual != expected:
            raise ValueError(
                "evento canonico ja possui evidencia de reconciliacao "
                "divergente"
            )

        evidence_write_count = 0

    for update in updates:
        _apply_update(events_by_id[update.event_id], update)

    await db.flush()

    return build_reconciliation_execution_report(
        updates,
        decision=CorporateEventReconciliationDecision.MATCHED,
        database_writes_executed=len(updates) + evidence_write_count,
    )
