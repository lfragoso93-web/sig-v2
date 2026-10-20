"""Dry-run read-only para reconciliacao de eventos corporativos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

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
from app.services.corporate_action_position_reader import (
    _component_bonus_projection_spec,
)
import json


def evidence_from_event(event: CorporateEvent) -> CorporateEventEvidence:
    payload = event.raw_metadata if isinstance(event.raw_metadata, dict) else {}
    if not payload and event.raw_data:
        try:
            parsed = json.loads(event.raw_data)
        except (TypeError, ValueError):
            parsed = {}
        if isinstance(parsed, dict):
            provider_payload = parsed.get("provider_payload")
            payload = provider_payload if isinstance(provider_payload, dict) else parsed
    settlement = payload.get("fractional_component_settlement")
    projection_reference = None
    if isinstance(settlement, dict):
        ref = str(settlement.get("evidence_reference", "")).strip()
        probe = SimpleNamespace(
            decision="MATCHED",
            evidence_type="OFFICIAL_ISSUER_DOCUMENT",
            evidence_reference=ref,
        )
        if ref and _component_bonus_projection_spec(event, probe) is not None:
            projection_reference = ref
    return CorporateEventEvidence(
        event_id=int(event.id),
        ticker=str(event.ticker),
        event_type=str(event.event_type),
        source_provider=str(event.source_provider),
        source_event_id=event.source_event_id,
        component_projection_reference=projection_reference,
    )


def _validate_effective_date(
    event: CorporateEvent,
    *,
    effective_date: date | None,
) -> None:
    is_b3 = str(event.source_provider or "").lower() == "b3"
    if effective_date is not None and not is_b3:
        raise ValueError("effective-date manual so e aceita para evento B3")
    if not is_b3:
        return
    if effective_date is None and event.effective_date is None:
        raise ValueError(
            "evento B3 sem data efetiva exige evidencia efetiva no MATCHED"
        )
    if effective_date is not None:
        if event.record_date is not None and effective_date <= event.record_date:
            raise ValueError(
                "data efetiva B3 deve ser posterior ao ultimo dia com direito"
            )
        if event.effective_date is not None and event.effective_date != effective_date:
            raise ValueError("data efetiva B3 diverge da data ja persistida")
        if event.effective_date is None and event.record_date is None:
            raise ValueError(
                "evento B3 sem ultimo dia com direito nao permite resolucao efetiva"
            )


def _normalized_decimal_text(value: object | None) -> str | None:
    if value is None:
        return None
    return str(Decimal(str(value)).normalize())


def _evidence_updates_for_missing_ledger_contract(
    actual: dict[str, object | None],
    expected: dict[str, object | None],
) -> dict[str, object]:
    immutable_fields = (
        "decision",
        "evidence_type",
        "evidence_reference",
        "fractional_policy",
        "fractional_quantity",
        "fractional_settlement_price",
        "cash_treatment",
    )
    for field in immutable_fields:
        if actual[field] != expected[field]:
            raise ValueError(
                "evento canonico ja possui evidencia de reconciliacao "
                "divergente"
            )

    if (
        expected.get("effective_date") is not None
        and actual.get("effective_date") not in {
            None,
            expected.get("effective_date"),
        }
    ):
        raise ValueError(
            "evento canonico ja possui evidencia de reconciliacao divergente"
        )

    updates: dict[str, object] = {}
    for field in (
        "ledger_basis",
        "ledger_transformation_reference",
        "ledger_quantity_factor",
    ):
        if actual[field] == expected[field]:
            continue
        if actual[field] is not None or expected[field] is None:
            raise ValueError(
                "evento canonico ja possui evidencia de reconciliacao "
                "divergente"
            )
        updates[field] = expected[field]
    if (
        actual.get("effective_date") is None
        and expected.get("effective_date") is not None
    ):
        updates["effective_date"] = expected.get("effective_date")
    return updates


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

    if (
        decision == CorporateEventReconciliationDecision.MATCHED
        and canonical_event_id is not None
        and match_resolution_evidence is not None
    ):
        canonical_event = next(
            event for event in events if int(event.id) == canonical_event_id
        )
        _validate_effective_date(
            canonical_event,
            effective_date=match_resolution_evidence.effective_date,
        )
        if match_resolution_evidence.ledger_basis is not None:
            existing_evidence_result = await db.execute(
                select(CorporateEventReconciliationEvidence).where(
                    CorporateEventReconciliationEvidence.corporate_event_id
                    == canonical_event_id
                )
            )
            existing_evidence = existing_evidence_result.scalar_one_or_none()
            if (
                existing_evidence is not None
                and existing_evidence.ledger_basis is not None
                and existing_evidence.ledger_basis
                != match_resolution_evidence.ledger_basis.value
            ):
                raise ValueError(
                    "evento canonico ja possui base de ledger divergente"
                )

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
        effective_date=(
            match_resolution_evidence.effective_date
            if match_resolution_evidence is not None
            and ledger_event.id == canonical_event_id
            else None
        ),
        component_bonus_evidence_type=(
            match_resolution_evidence.evidence_type.value
            if match_resolution_evidence is not None
            and ledger_event.id == canonical_event_id
            else None
        ),
        component_bonus_evidence_reference=(
            match_resolution_evidence.evidence_reference
            if match_resolution_evidence is not None
            and ledger_event.id == canonical_event_id
            else None
        ),
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

    canonical_event = events_by_id[canonical_event_id]
    effective_date = match_resolution_evidence.effective_date
    _validate_effective_date(canonical_event, effective_date=effective_date)
    if match_resolution_evidence.ledger_basis is not None:
        existing_basis_result = await db.execute(
            select(CorporateEventReconciliationEvidence).where(
                CorporateEventReconciliationEvidence.corporate_event_id
                == canonical_event_id
            )
        )
        existing_basis_evidence = existing_basis_result.scalar_one_or_none()
        if (
            existing_basis_evidence is not None
            and existing_basis_evidence.ledger_basis is not None
            and existing_basis_evidence.ledger_basis
            != match_resolution_evidence.ledger_basis.value
        ):
            raise ValueError("evento canonico ja possui base de ledger divergente")
    if effective_date is not None:
        canonical_event.effective_date = effective_date

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
        "ledger_basis": (
            match_resolution_evidence.ledger_basis.value
            if match_resolution_evidence.ledger_basis is not None
            else None
        ),
        "ledger_transformation_reference": (
            match_resolution_evidence.ledger_transformation_reference
        ),
        "ledger_quantity_factor": _normalized_decimal_text(
            match_resolution_evidence.ledger_quantity_factor
        ),
        "effective_date": (
            match_resolution_evidence.effective_date.isoformat()
            if match_resolution_evidence.effective_date is not None
            else None
        ),
    }

    if existing is None:
        db.add(
            CorporateEventReconciliationEvidence(
                corporate_event_id=canonical_event_id,
                **{
                    **expected,
                    "effective_date": canonical_event.effective_date,
                },
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
            "ledger_basis": existing.ledger_basis,
            "ledger_transformation_reference": (
                existing.ledger_transformation_reference
            ),
            "ledger_quantity_factor": _normalized_decimal_text(
                existing.ledger_quantity_factor
            ),
            "effective_date": (
                existing.effective_date.isoformat()
                if existing.effective_date is not None
                else None
            ),
        }

        missing_ledger_updates = _evidence_updates_for_missing_ledger_contract(
            actual,
            expected,
        )
        for field, value in missing_ledger_updates.items():
            setattr(existing, field, value)

        evidence_write_count = 1 if missing_ledger_updates else 0

    for update in updates:
        _apply_update(events_by_id[update.event_id], update)

    await db.flush()

    return build_reconciliation_execution_report(
        updates,
        decision=CorporateEventReconciliationDecision.MATCHED,
        database_writes_executed=len(updates) + evidence_write_count,
    )
