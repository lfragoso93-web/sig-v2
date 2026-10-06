"""Pure tests for guarded real-data certification plans."""

import pytest
from app.services.real_data_certification_contract import (
    REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION,
    REQUIRED_PROMOTION_CHECKS,
    RealDataCertificationAction,
    RealDataCertificationValidationError,
    build_real_data_certification_plan,
    validate_execution_confirmation,
)
from app.services.real_data_certification_reader import RealDataCertificationIdentity


def _identity(**overrides: str) -> RealDataCertificationIdentity:
    values = {
        "environment": "local-canonical",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
        "dataset_reference": "dataset:2026-10-06",
        "alembic_revision": "20261005_real_data_certification",
        "gate_issue_reference": "#227",
        "pull_request_reference": "#362",
    }
    values.update(overrides)
    return RealDataCertificationIdentity(**values)


def _evidence(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "schema_version": REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION,
        "status": "GO",
        "dataset_reference": "dataset:2026-10-06",
        "ready_for_real_data": False,
        "database_writes_executed": 0,
        "blockers": [],
        "warnings": [],
        "checks": {check: True for check in REQUIRED_PROMOTION_CHECKS},
    }
    values.update(overrides)
    return values


def test_promotion_plan_is_deterministic_and_dry_run() -> None:
    first = build_real_data_certification_plan(
        action=RealDataCertificationAction.PROMOTE,
        identity=_identity(),
        evidence_payload=_evidence(),
        actor="operator@example.test",
        reason="formal approval",
    )
    second = build_real_data_certification_plan(
        action=RealDataCertificationAction.PROMOTE,
        identity=_identity(),
        evidence_payload=_evidence(),
        actor="operator@example.test",
        reason="formal approval",
    )

    assert first.event_key == second.event_key
    assert first.dry_run is True
    assert first.database_writes_executed == 0
    assert first.confirmation.startswith("PROMOTE REAL DATA ON local-canonical")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "GO_ASSISTED", "status must be GO"),
        ("ready_for_real_data", True, "closed pre-promotion state"),
        ("database_writes_executed", 1, "zero database writes"),
        ("blockers", ["open"], "zero blockers"),
        ("warnings", ["open"], "zero warnings"),
        ("dataset_reference", "dataset:other", "differs from target identity"),
    ],
)
def test_promotion_rejects_unsafe_evidence(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(RealDataCertificationValidationError, match=message):
        build_real_data_certification_plan(
            action=RealDataCertificationAction.PROMOTE,
            identity=_identity(),
            evidence_payload=_evidence(**{field: value}),
            actor="operator",
            reason="approval",
        )


def test_promotion_rejects_incomplete_or_failed_check_set() -> None:
    with pytest.raises(RealDataCertificationValidationError, match="required check set"):
        build_real_data_certification_plan(
            action=RealDataCertificationAction.PROMOTE,
            identity=_identity(),
            evidence_payload=_evidence(checks={"readiness": True}),
            actor="operator",
            reason="approval",
        )

    checks = {check: True for check in REQUIRED_PROMOTION_CHECKS}
    checks["services"] = False
    with pytest.raises(RealDataCertificationValidationError, match="must pass"):
        build_real_data_certification_plan(
            action=RealDataCertificationAction.PROMOTE,
            identity=_identity(),
            evidence_payload=_evidence(checks=checks),
            actor="operator",
            reason="approval",
        )


def test_promotion_requires_formal_gate_and_structural_pr() -> None:
    with pytest.raises(RealDataCertificationValidationError, match="#227"):
        build_real_data_certification_plan(
            action=RealDataCertificationAction.PROMOTE,
            identity=_identity(gate_issue_reference="#999"),
            evidence_payload=_evidence(),
            actor="operator",
            reason="approval",
        )
    with pytest.raises(RealDataCertificationValidationError, match="#362"):
        build_real_data_certification_plan(
            action=RealDataCertificationAction.PROMOTE,
            identity=_identity(pull_request_reference="#999"),
            evidence_payload=_evidence(),
            actor="operator",
            reason="approval",
        )


def test_revocation_requires_existing_event_and_reason_evidence() -> None:
    with pytest.raises(RealDataCertificationValidationError, match="must supersede"):
        build_real_data_certification_plan(
            action=RealDataCertificationAction.REVOKE,
            identity=_identity(),
            evidence_payload={"blockers": ["operator_requested"]},
            actor="operator",
            reason="revoke",
        )

    plan = build_real_data_certification_plan(
        action=RealDataCertificationAction.REVOKE,
        identity=_identity(),
        evidence_payload={"blockers": ["operator_requested"]},
        actor="operator",
        reason="revoke",
        supersedes_event_id=7,
        supersedes_event_key="promote-1",
    )
    assert plan.action is RealDataCertificationAction.REVOKE
    assert plan.supersedes_event_id == 7


def test_execution_confirmation_must_match_exact_plan() -> None:
    plan = build_real_data_certification_plan(
        action=RealDataCertificationAction.PROMOTE,
        identity=_identity(),
        evidence_payload=_evidence(),
        actor="operator",
        reason="approval",
    )

    with pytest.raises(RealDataCertificationValidationError, match="does not match"):
        validate_execution_confirmation(plan, "yes")
    validate_execution_confirmation(plan, plan.confirmation)
