import pytest

from app.services.corporate_event_reconciliation_plan import (
    CorporateEventEvidence,
    CorporateEventMatchResolutionEvidence,
    CorporateEventReconciliationDecision,
    FractionalResolutionPolicy,
    build_reconciliation_execution_report,
    build_reconciliation_dry_run_report,
    plan_conflict_reconciliation,
    plan_matched_reconciliation,
    validate_match_resolution_evidence,
)


def _evidence(event_id: int, source: str = "brapi") -> CorporateEventEvidence:
    return CorporateEventEvidence(
        event_id=event_id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        source_provider=source,
        source_event_id=f"{source}:{event_id}",
    )


def test_conflict_plan_keeps_all_evidences_out_of_projection() -> None:
    updates = plan_conflict_reconciliation(
        (_evidence(13, "yahoo"), _evidence(12, "brapi")),
        reason="fonte e ledger divergem",
    )

    assert [update.event_id for update in updates] == [12, 13]
    assert {update.reconciliation_status for update in updates} == {"CONFLICT"}
    assert {update.requires_review for update in updates} == {True}
    assert {update.is_canonical for update in updates} == {False}
    assert {update.matched_event_id for update in updates} == {None}


def test_matched_plan_allows_one_canonical_event_only() -> None:
    updates = plan_matched_reconciliation(
        (_evidence(12, "brapi"), _evidence(13, "yahoo")),
        canonical_event_id=13,
        reason="fonte canonica validada contra extrato",
    )

    canonical = [update for update in updates if update.event_id == 13][0]
    duplicate = [update for update in updates if update.event_id == 12][0]

    assert canonical.reconciliation_status == "MATCHED"
    assert canonical.requires_review is False
    assert canonical.is_canonical is True
    assert canonical.matched_event_id is None
    assert duplicate.reconciliation_status == "CONFLICT"
    assert duplicate.requires_review is True
    assert duplicate.is_canonical is False
    assert duplicate.matched_event_id == 13


def test_plan_rejects_unknown_canonical_event() -> None:
    with pytest.raises(ValueError, match="evento canonico"):
        plan_matched_reconciliation(
            (_evidence(12),),
            canonical_event_id=13,
            reason="invalido",
        )


def test_plan_requires_non_empty_reason() -> None:
    with pytest.raises(ValueError, match="motivo"):
        plan_conflict_reconciliation((_evidence(12),), reason=" ")


def test_dry_run_report_is_versioned_and_read_only() -> None:
    report = build_reconciliation_dry_run_report(
        (_evidence(12), _evidence(13, "yahoo")),
        decision=CorporateEventReconciliationDecision.CONFLICT,
        reason="duplicidade sem reconciliacao de fracao",
    )

    payload = report.to_dict()

    assert payload["schema_version"] == "corporate-event-reconciliation-dry-run.v1"
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["database_writes_executed"] == 0
    assert payload["event_ids"] == [12, 13]
    assert {item["reconciliation_status"] for item in payload["updates"]} == {
        "CONFLICT",
    }


def test_execution_report_records_write_count() -> None:
    updates = plan_conflict_reconciliation(
        (_evidence(12), _evidence(13, "yahoo")),
        reason="persistir conflito",
    )

    report = build_reconciliation_execution_report(
        updates,
        decision=CorporateEventReconciliationDecision.CONFLICT,
        database_writes_executed=2,
    )
    payload = report.to_dict()

    assert payload["schema_version"] == "corporate-event-reconciliation-execution.v1"
    assert payload["dry_run"] is False
    assert payload["database_writes_executed"] == 2
    assert payload["event_ids"] == [12, 13]


def test_match_resolution_requires_broker_statement_reference() -> None:
    with pytest.raises(ValueError, match="extrato/corretora"):
        validate_match_resolution_evidence(
            CorporateEventMatchResolutionEvidence(
                broker_statement_reference=" ",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
            )
        )


def test_match_resolution_allows_no_fractional_residue() -> None:
    validate_match_resolution_evidence(
        CorporateEventMatchResolutionEvidence(
            broker_statement_reference="broker-note:AMOB3:2025-05",
            fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        )
    )


def test_match_resolution_requires_cash_settlement_details_for_fraction() -> None:
    with pytest.raises(ValueError, match="preco de liquidacao"):
        validate_match_resolution_evidence(
            CorporateEventMatchResolutionEvidence(
                broker_statement_reference="broker-note:KLBN11:2025-12",
                fractional_policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
                fractional_quantity="0.10",
            )
        )


def test_match_resolution_rejects_manual_review_for_matched() -> None:
    with pytest.raises(ValueError, match="nao autoriza MATCHED"):
        validate_match_resolution_evidence(
            CorporateEventMatchResolutionEvidence(
                broker_statement_reference="broker-note:KLBN11:2025-12",
                fractional_policy=FractionalResolutionPolicy.MANUAL_REVIEW,
            )
        )
