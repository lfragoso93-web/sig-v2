import pytest
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventEvidence,
    CorporateEventMatchEvidenceType,
    CorporateEventMatchResolutionEvidence,
    CorporateEventLedgerBasis,
    CorporateEventReconciliationDecision,
    FractionalResolutionPolicy,
    build_reconciliation_dry_run_report,
    build_reconciliation_execution_report,
    plan_conflict_reconciliation,
    plan_matched_reconciliation,
    validate_match_resolution_evidence,
)


def _evidence(event_id: int, source: str = "brapi") -> CorporateEventEvidence:
    return CorporateEventEvidence(
        event_id=event_id,
        ticker="ABEV3",
        event_type="GRUPAMENTO",
        source_provider=source,
        source_event_id=f"{source}:{event_id}",
    )


def _ticker_evidence(
    event_id: int,
    ticker: str,
    source: str = "brapi",
) -> CorporateEventEvidence:
    return CorporateEventEvidence(
        event_id=event_id,
        ticker=ticker,
        event_type="BONIFICACAO",
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
    assert "match_resolution_evidence" not in payload


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


def test_match_resolution_requires_document_reference() -> None:
    with pytest.raises(ValueError, match="referencia documental"):
        validate_match_resolution_evidence(
            CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference=" ",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
            )
        )


def test_match_resolution_allows_no_fractional_residue() -> None:
    validate_match_resolution_evidence(
        CorporateEventMatchResolutionEvidence(
            evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference="broker-note:AMOB3:2025-05",
            fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        )
    )


def test_match_resolution_serializes_explicit_ledger_basis() -> None:
    evidence = CorporateEventMatchResolutionEvidence(
        evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
        evidence_reference="broker-note:AMOB3:2025-05",
        fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        ledger_basis=CorporateEventLedgerBasis.ADJUSTED_POST_EVENT,
    )

    validate_match_resolution_evidence(evidence)

    assert evidence.to_dict()["ledger_basis"] == "ADJUSTED_POST_EVENT"


def test_match_resolution_requires_cash_settlement_details_for_fraction() -> None:
    with pytest.raises(ValueError, match="preco de liquidacao"):
        validate_match_resolution_evidence(
            CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference="broker-note:KLBN11:2025-12",
                fractional_policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
                fractional_quantity="0.10",
            )
        )


def test_matched_cash_settlement_keeps_klbn11_fail_closed_until_unit_contract() -> None:
    with pytest.raises(ValueError, match="KLBN11 exige contrato explicito"):
        build_reconciliation_dry_run_report(
            (_ticker_evidence(12, "KLBN11"), _ticker_evidence(13, "KLBN11", "yahoo")),
            decision=CorporateEventReconciliationDecision.MATCHED,
            reason="unit composta exige decomposicao por especies",
            canonical_event_id=12,
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
                evidence_reference="broker-note:KLBN11:2025-12",
                fractional_policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
                fractional_quantity="0.10",
                fractional_settlement_price="4.00",
                cash_treatment="AUCTION_SETTLEMENT",
            ),
        )


def test_matched_grouping_keeps_amob3_fail_closed_until_ledger_basis_contract() -> None:
    with pytest.raises(ValueError, match="AMOB3 exige contrato explicito"):
        build_reconciliation_dry_run_report(
            (
                CorporateEventEvidence(
                    event_id=12,
                    ticker="AMOB3",
                    event_type="GRUPAMENTO",
                    source_provider="brapi",
                    source_event_id="brapi:amob3",
                ),
                CorporateEventEvidence(
                    event_id=13,
                    ticker="AMOB3",
                    event_type="GRUPAMENTO",
                    source_provider="yahoo",
                    source_event_id="yahoo:amob3",
                ),
            ),
            decision=CorporateEventReconciliationDecision.MATCHED,
            reason="ledger pode ja estar ajustado pelo grupamento",
            canonical_event_id=12,
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
                evidence_reference="broker-note:AMOB3:2025-05",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
            ),
        )


def test_matched_grouping_rejects_amob3_adjusted_ledger_reapplication() -> None:
    with pytest.raises(ValueError, match="reaplicacao sobre ledger ajustado"):
        build_reconciliation_dry_run_report(
            (
                CorporateEventEvidence(
                    event_id=12,
                    ticker="AMOB3",
                    event_type="GRUPAMENTO",
                    source_provider="brapi",
                    source_event_id="brapi:amob3",
                ),
            ),
            decision=CorporateEventReconciliationDecision.MATCHED,
            reason="ledger ja ajustado pelo grupamento",
            canonical_event_id=12,
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
                evidence_reference="broker-note:AMOB3:2025-05",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
                ledger_basis=CorporateEventLedgerBasis.ADJUSTED_POST_EVENT,
            ),
        )


def test_matched_grouping_keeps_amob3_raw_ledger_fail_closed() -> None:
    with pytest.raises(ValueError, match="ledger historico bruto"):
        build_reconciliation_dry_run_report(
            (
                CorporateEventEvidence(
                    event_id=12,
                    ticker="AMOB3",
                    event_type="GRUPAMENTO",
                    source_provider="brapi",
                    source_event_id="brapi:amob3",
                ),
            ),
            decision=CorporateEventReconciliationDecision.MATCHED,
            reason="ledger historico ainda nao transformado",
            canonical_event_id=12,
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
                evidence_reference="broker-note:AMOB3:2025-05",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
                ledger_basis=CorporateEventLedgerBasis.RAW_HISTORICAL,
            ),
        )


def test_match_resolution_rejects_manual_review_for_matched() -> None:
    with pytest.raises(ValueError, match="nao autoriza MATCHED"):
        validate_match_resolution_evidence(
            CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference="broker-note:KLBN11:2025-12",
                fractional_policy=FractionalResolutionPolicy.MANUAL_REVIEW,
            )
        )


def test_matched_dry_run_requires_operational_evidence() -> None:
    with pytest.raises(ValueError, match="evidencia operacional"):
        build_reconciliation_dry_run_report(
            (_evidence(12), _evidence(13, "yahoo")),
            decision=CorporateEventReconciliationDecision.MATCHED,
            reason="fonte canonica validada contra extrato",
            canonical_event_id=13,
        )


def test_matched_dry_run_validates_operational_evidence() -> None:
    with pytest.raises(ValueError, match="nao autoriza MATCHED"):
        build_reconciliation_dry_run_report(
            (_evidence(12), _evidence(13, "yahoo")),
            decision=CorporateEventReconciliationDecision.MATCHED,
            reason="aguarda revisao operacional",
            canonical_event_id=13,
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference="broker-note:AMOB3:2025-05",
                fractional_policy=FractionalResolutionPolicy.MANUAL_REVIEW,
            ),
        )


def test_matched_dry_run_accepts_valid_operational_evidence() -> None:
    report = build_reconciliation_dry_run_report(
        (_evidence(12), _evidence(13, "yahoo")),
        decision=CorporateEventReconciliationDecision.MATCHED,
        reason="fonte canonica validada contra extrato",
        canonical_event_id=13,
        match_resolution_evidence=CorporateEventMatchResolutionEvidence(
            evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference="broker-note:AMOB3:2025-05",
            fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        ),
    )

    assert report.dry_run is True
    assert report.database_writes_executed == 0
    assert report.decision == "MATCHED"
    assert [update.event_id for update in report.updates] == [12, 13]
    assert [update.event_id for update in report.updates if update.is_canonical] == [13]


def test_conflict_dry_run_rejects_matched_evidence() -> None:
    with pytest.raises(ValueError, match="CONFLICT nao aceita evidencia"):
        build_reconciliation_dry_run_report(
            (_evidence(12), _evidence(13, "yahoo")),
            decision=CorporateEventReconciliationDecision.CONFLICT,
            reason="fontes conflitantes",
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT, evidence_reference="broker-note:AMOB3:2025-05",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
            ),
        )


def test_conflict_dry_run_rejects_canonical_event_id() -> None:
    with pytest.raises(ValueError, match="CONFLICT nao aceita canonical_event_id"):
        build_reconciliation_dry_run_report(
            (_evidence(12), _evidence(13, "yahoo")),
            decision=CorporateEventReconciliationDecision.CONFLICT,
            reason="fontes conflitantes",
            canonical_event_id=12,
        )


def test_matched_dry_run_serializes_official_evidence_as_v2() -> None:
    report = build_reconciliation_dry_run_report(
        (_evidence(12), _evidence(13, "yahoo")),
        decision=CorporateEventReconciliationDecision.MATCHED,
        reason="evento validado por documento oficial",
        canonical_event_id=13,
        match_resolution_evidence=CorporateEventMatchResolutionEvidence(
            evidence_type=CorporateEventMatchEvidenceType.OFFICIAL_EXCHANGE_DOCUMENT,
            evidence_reference="b3:official-document:AMOB3:2025-05",
            fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        ),
    )

    payload = report.to_dict()

    assert payload["schema_version"] == "corporate-event-reconciliation-dry-run.v2"
    assert payload["match_resolution_evidence"] == {
        "evidence_type": "OFFICIAL_EXCHANGE_DOCUMENT",
        "evidence_reference": "b3:official-document:AMOB3:2025-05",
        "fractional_policy": "NO_FRACTIONAL_RESIDUE",
        "fractional_quantity": None,
        "fractional_settlement_price": None,
        "cash_treatment": None,
        "ledger_basis": None,
    }
    assert payload["database_writes_executed"] == 0
