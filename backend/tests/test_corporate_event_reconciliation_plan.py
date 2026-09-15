import pytest

from app.services.corporate_event_reconciliation_plan import (
    CorporateEventEvidence,
    plan_conflict_reconciliation,
    plan_matched_reconciliation,
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
