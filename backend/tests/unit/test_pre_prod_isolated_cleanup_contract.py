from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.pre_prod_isolated_cleanup_contract import (
    APPROVED_BRANCH,
    APPROVED_PLAN_MODE,
    APPROVED_PLAN_SCHEMA_VERSION,
    ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
    REQUIRED_ISOLATION_MARKER,
    ApprovedCleanupPlanIdentity,
    CleanupDatabaseIdentity,
    CleanupExecutionConfirmation,
    IsolatedCleanupAuthorization,
    IsolatedCleanupValidationError,
    canonical_json_sha256,
    validate_approved_plan,
)

RUN_ID = "20260723-095541"
COMMIT_SHA = "ced26b73658f405cabf93e690e40fae836e70d0b"


def _plan_payload() -> dict[str, object]:
    return {
        "schema_version": APPROVED_PLAN_SCHEMA_VERSION,
        "mode": APPROVED_PLAN_MODE,
        "run_id": RUN_ID,
        "branch": APPROVED_BRANCH,
        "commit_sha": COMMIT_SHA,
        "cleanup_order": ["asset_prices", "transactions"],
        "blockers": [],
        "safety": {
            "plan_only": True,
            "database_writes_executed": 0,
            "cleanup_executed": False,
            "rebuild_executed": False,
        },
    }


def _validated_plan() -> ApprovedCleanupPlanIdentity:
    payload = _plan_payload()
    checksum = canonical_json_sha256(payload)
    return validate_approved_plan(
        payload=payload,
        expected_run_id=RUN_ID,
        expected_commit_sha=COMMIT_SHA,
        expected_plan_sha256=checksum,
    )


def _database(
    database: str,
    *,
    marker: str | None = None,
) -> CleanupDatabaseIdentity:
    return CleanupDatabaseIdentity(
        host="db",
        port=5432,
        database=database,
        isolation_marker=marker,
    )


def _confirmation(plan: ApprovedCleanupPlanIdentity) -> CleanupExecutionConfirmation:
    expected = (
        f"CLEANUP {plan.run_id} ON sig_v2_cleanup_test "
        f"AT {plan.commit_sha} WITH {plan.plan_sha256}"
    )
    return CleanupExecutionConfirmation(
        run_id=plan.run_id,
        target_database="sig_v2_cleanup_test",
        commit_sha=plan.commit_sha,
        plan_sha256=plan.plan_sha256,
        confirmation=expected,
    )


def test_validate_approved_plan_accepts_integral_plan() -> None:
    plan = _validated_plan()

    assert plan.run_id == RUN_ID
    assert plan.commit_sha == COMMIT_SHA
    assert plan.cleanup_order == ("asset_prices", "transactions")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "legacy.v1", "schema_version"),
        ("mode", "execute", "plan mode"),
        ("branch", "main", "stable-15jun"),
        ("run_id", "other-run", "run_id"),
        ("commit_sha", "0" * 40, "commit_sha"),
        ("blockers", ["cycle"], "blockers"),
    ],
)
def test_validate_approved_plan_rejects_identity_or_gate_divergence(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = _plan_payload()
    payload[field] = value
    checksum = canonical_json_sha256(payload)

    with pytest.raises(IsolatedCleanupValidationError, match=message):
        validate_approved_plan(
            payload=payload,
            expected_run_id=RUN_ID,
            expected_commit_sha=COMMIT_SHA,
            expected_plan_sha256=checksum,
        )


def test_validate_approved_plan_rejects_checksum_divergence() -> None:
    payload = _plan_payload()

    with pytest.raises(IsolatedCleanupValidationError, match="checksum"):
        validate_approved_plan(
            payload=payload,
            expected_run_id=RUN_ID,
            expected_commit_sha=COMMIT_SHA,
            expected_plan_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("safety_field", "value"),
    [
        ("plan_only", False),
        ("database_writes_executed", 1),
        ("cleanup_executed", True),
        ("rebuild_executed", True),
    ],
)
def test_validate_approved_plan_rejects_unsafe_history(
    safety_field: str,
    value: object,
) -> None:
    payload = _plan_payload()
    safety = dict(payload["safety"])  # type: ignore[arg-type]
    safety[safety_field] = value
    payload["safety"] = safety
    checksum = canonical_json_sha256(payload)

    with pytest.raises(IsolatedCleanupValidationError):
        validate_approved_plan(
            payload=payload,
            expected_run_id=RUN_ID,
            expected_commit_sha=COMMIT_SHA,
            expected_plan_sha256=checksum,
        )


def test_confirmation_is_bound_to_run_database_commit_and_plan() -> None:
    plan = _validated_plan()
    confirmation = _confirmation(plan)

    assert confirmation.confirmation == confirmation.expected_confirmation


@pytest.mark.parametrize(
    "confirmation",
    [
        "CLEANUP another-run ON sig_v2_cleanup_test AT " + COMMIT_SHA + " WITH " + "0" * 64,
        "yes",
        "",
    ],
)
def test_confirmation_rejects_non_exact_text(confirmation: str) -> None:
    plan = _validated_plan()

    with pytest.raises(IsolatedCleanupValidationError, match="confirmation"):
        CleanupExecutionConfirmation(
            run_id=plan.run_id,
            target_database="sig_v2_cleanup_test",
            commit_sha=plan.commit_sha,
            plan_sha256=plan.plan_sha256,
            confirmation=confirmation,
        )


def test_authorization_accepts_distinct_marked_target() -> None:
    plan = _validated_plan()
    authorization = IsolatedCleanupAuthorization(
        schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
        plan=plan,
        source=_database("sig_v2"),
        target=_database(
            "sig_v2_cleanup_test",
            marker=REQUIRED_ISOLATION_MARKER,
        ),
        confirmation=_confirmation(plan),
    )

    payload = authorization.to_dict()

    assert payload["source"] == {"database": "db:5432/sig_v2"}
    assert payload["target"] == {
        "database": "db:5432/sig_v2_cleanup_test",
        "isolation_marker": REQUIRED_ISOLATION_MARKER,
    }
    assert "confirmation" not in payload["confirmation"]


def test_authorization_rejects_source_as_target() -> None:
    plan = _validated_plan()
    source = _database("sig_v2_cleanup_test", marker=REQUIRED_ISOLATION_MARKER)

    with pytest.raises(IsolatedCleanupValidationError, match="different"):
        IsolatedCleanupAuthorization(
            schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
            plan=plan,
            source=source,
            target=source,
            confirmation=_confirmation(plan),
        )


def test_authorization_rejects_target_without_isolation_marker() -> None:
    plan = _validated_plan()

    with pytest.raises(
        IsolatedCleanupValidationError,
        match="supported execution marker",
    ):
        IsolatedCleanupAuthorization(
            schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
            plan=plan,
            source=_database("sig_v2"),
            target=_database("sig_v2_cleanup_test"),
            confirmation=_confirmation(plan),
        )


def test_authorization_rejects_confirmation_from_other_plan() -> None:
    plan = _validated_plan()
    other_plan = replace(plan, plan_sha256="f" * 64)

    with pytest.raises(IsolatedCleanupValidationError, match="plan_sha256"):
        IsolatedCleanupAuthorization(
            schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
            plan=other_plan,
            source=_database("sig_v2"),
            target=_database(
                "sig_v2_cleanup_test",
                marker=REQUIRED_ISOLATION_MARKER,
            ),
            confirmation=_confirmation(plan),
        )
