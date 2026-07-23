from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.pre_prod_isolated_cleanup_contract import (
    ApprovedCleanupPlanIdentity,
    CleanupDatabaseIdentity,
    CleanupExecutionConfirmation,
    IsolatedCleanupAuthorization,
    ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
    REQUIRED_ISOLATION_MARKER,
)
from app.services.pre_prod_isolated_cleanup_executor import (
    CleanupTableExecution,
    IsolatedCleanupExecutionResult,
)
from app.services.pre_prod_isolated_cleanup_report import (
    IsolatedCleanupReportAlreadyExistsError,
    IsolatedCleanupReportError,
    build_execution_report,
    build_failure_report,
    execution_report_path,
    publish_execution_report,
)

RUN_ID = "20260723-180000"
COMMIT_SHA = "a" * 40
PLAN_SHA256 = "b" * 64
TARGET_DATABASE = "sgi_v2_cleanup_isolated"


def _authorization() -> IsolatedCleanupAuthorization:
    plan = ApprovedCleanupPlanIdentity(
        run_id=RUN_ID,
        branch="stable-15jun",
        commit_sha=COMMIT_SHA,
        plan_sha256=PLAN_SHA256,
        cleanup_order=("transactions", "assets"),
    )
    target = CleanupDatabaseIdentity(
        host="isolated-db",
        port=5432,
        database=TARGET_DATABASE,
        isolation_marker=REQUIRED_ISOLATION_MARKER,
    )
    confirmation_value = (
        f"CLEANUP {RUN_ID} ON {TARGET_DATABASE} "
        f"AT {COMMIT_SHA} WITH {PLAN_SHA256}"
    )
    return IsolatedCleanupAuthorization(
        schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
        plan=plan,
        source=CleanupDatabaseIdentity(
            host="pre-prod-db",
            port=5432,
            database="sgi_v2_pre_prod",
        ),
        target=target,
        confirmation=CleanupExecutionConfirmation(
            run_id=RUN_ID,
            target_database=TARGET_DATABASE,
            commit_sha=COMMIT_SHA,
            plan_sha256=PLAN_SHA256,
            confirmation=confirmation_value,
        ),
    )


def _result() -> IsolatedCleanupExecutionResult:
    return IsolatedCleanupExecutionResult(
        run_id=RUN_ID,
        target_database="isolated-db:5432/sgi_v2_cleanup_isolated",
        plan_sha256=PLAN_SHA256,
        lock_acquired=True,
        committed=True,
        tables=(
            CleanupTableExecution(
                table_name="transactions",
                expected_rows_before=3,
                actual_rows_before=3,
                deleted_rows=3,
                actual_rows_after=0,
            ),
            CleanupTableExecution(
                table_name="assets",
                expected_rows_before=2,
                actual_rows_before=2,
                deleted_rows=2,
                actual_rows_after=0,
            ),
        ),
    )


def test_build_execution_report_redacts_target_and_reconciles_totals() -> None:
    report = build_execution_report(
        authorization=_authorization(),
        result=_result(),
        started_at="2026-07-23T18:00:00+00:00",
        finished_at="2026-07-23T18:00:01+00:00",
    )

    payload = report.to_dict()
    assert payload["schema_version"] == ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION
    assert payload["target_database"] == "isolated-db:5432/sgi_v2_cleanup_isolated"
    assert "password" not in json.dumps(payload).lower()
    assert payload["final_state"] == "committed"
    assert payload["preserved_tables_unchanged"] is True
    assert payload["rebuild_started"] is False
    assert payload["cleanup_order"] == ("transactions", "assets")
    assert payload["totals"] == {
        "tables": 2,
        "rows_before": 5,
        "rows_deleted": 5,
        "rows_after": 0,
        "database_writes": 5,
    }


def test_build_failure_report_is_redacted_and_zero_write() -> None:
    report = build_failure_report(
        authorization=_authorization(),
        started_at="2026-07-23T18:00:00+00:00",
        finished_at="2026-07-23T18:00:01+00:00",
        final_state="rolled_back",
        abort_reason="postcondition_failed",
        lock_acquired=True,
    )

    payload = report.to_dict()
    serialized = json.dumps(payload)
    assert payload["final_state"] == "rolled_back"
    assert payload["committed"] is False
    assert payload["abort_reason"] == "postcondition_failed"
    assert payload["totals"]["database_writes"] == 0
    assert payload["tables"] == ()
    assert "secret" not in serialized
    assert "postgresql://" not in serialized


@pytest.mark.parametrize(
    ("final_state", "abort_reason"),
    [
        ("committed", "unexpected"),
        ("aborted", "raw exception message"),
        ("rolled_back", ""),
    ],
)
def test_build_failure_report_rejects_unsafe_contract(
    final_state: str,
    abort_reason: str,
) -> None:
    with pytest.raises(IsolatedCleanupReportError):
        build_failure_report(
            authorization=_authorization(),
            started_at="start",
            finished_at="finish",
            final_state=final_state,
            abort_reason=abort_reason,
            lock_acquired=False,
        )


def test_build_execution_report_rejects_mismatched_result() -> None:
    result = IsolatedCleanupExecutionResult(
        run_id="other-run",
        target_database="isolated-db:5432/sgi_v2_cleanup_isolated",
        plan_sha256=PLAN_SHA256,
        lock_acquired=True,
        committed=True,
        tables=(),
    )

    with pytest.raises(IsolatedCleanupReportError, match="run_id"):
        build_execution_report(
            authorization=_authorization(),
            result=result,
            started_at="start",
            finished_at="finish",
        )


def test_execution_report_path_rejects_unsafe_run_id(tmp_path: Path) -> None:
    with pytest.raises(IsolatedCleanupReportError, match="run_id"):
        execution_report_path(run_id="../escape", artifact_root=tmp_path)


def test_publish_execution_report_writes_utf8_json_atomically(tmp_path: Path) -> None:
    report = build_execution_report(
        authorization=_authorization(),
        result=_result(),
        started_at="2026-07-23T18:00:00+00:00",
        finished_at="2026-07-23T18:00:01+00:00",
    )

    destination = publish_execution_report(
        report=report,
        artifact_root=tmp_path,
    )

    assert destination == tmp_path / RUN_ID / "cleanup" / "execution.json"
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["run_id"] == RUN_ID
    assert payload["committed"] is True
    assert not list(destination.parent.glob(".*.tmp"))


def test_publish_execution_report_never_overwrites(tmp_path: Path) -> None:
    report = build_execution_report(
        authorization=_authorization(),
        result=_result(),
        started_at="2026-07-23T18:00:00+00:00",
        finished_at="2026-07-23T18:00:01+00:00",
    )
    destination = publish_execution_report(report=report, artifact_root=tmp_path)
    original = destination.read_bytes()

    with pytest.raises(IsolatedCleanupReportAlreadyExistsError, match="already exists"):
        publish_execution_report(report=report, artifact_root=tmp_path)

    assert destination.read_bytes() == original
