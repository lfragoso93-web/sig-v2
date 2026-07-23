from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.services.pre_prod_isolated_cleanup_contract import (
    APPROVED_BRANCH,
    APPROVED_PLAN_MODE,
    APPROVED_PLAN_SCHEMA_VERSION,
    ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
    REQUIRED_ISOLATION_MARKER,
    CleanupDatabaseIdentity,
    CleanupExecutionConfirmation,
    IsolatedCleanupAuthorization,
    canonical_json_sha256,
    validate_approved_plan,
)
from app.services.pre_prod_isolated_cleanup_executor import (
    IsolatedCleanupCountMismatchError,
    IsolatedCleanupExecutionError,
    IsolatedCleanupLockUnavailableError,
    IsolatedCleanupPostconditionError,
    execute_isolated_cleanup,
)

RUN_ID = "20260723-104500"
COMMIT_SHA = "38ad47430d5abbf067b653c6c726952cde155e9c"


def _plan_payload() -> dict[str, Any]:
    return {
        "schema_version": APPROVED_PLAN_SCHEMA_VERSION,
        "mode": APPROVED_PLAN_MODE,
        "run_id": RUN_ID,
        "branch": APPROVED_BRANCH,
        "commit_sha": COMMIT_SHA,
        "cleanup_order": ["asset_prices", "transactions"],
        "tables": [
            {
                "name": "asset_prices",
                "classification": "rebuildable",
                "expected_rows_before": 2,
                "cleanup_position": 1,
            },
            {
                "name": "transactions",
                "classification": "export_before_cleanup",
                "expected_rows_before": 1,
                "cleanup_position": 2,
            },
        ],
        "blockers": [],
        "safety": {
            "plan_only": True,
            "database_writes_executed": 0,
            "cleanup_executed": False,
            "rebuild_executed": False,
        },
    }


def _authorization(payload: dict[str, Any]) -> IsolatedCleanupAuthorization:
    checksum = canonical_json_sha256(payload)
    plan = validate_approved_plan(
        payload=payload,
        expected_run_id=RUN_ID,
        expected_commit_sha=COMMIT_SHA,
        expected_plan_sha256=checksum,
    )
    confirmation_text = (
        f"CLEANUP {RUN_ID} ON sig_v2_cleanup_test "
        f"AT {COMMIT_SHA} WITH {checksum}"
    )
    return IsolatedCleanupAuthorization(
        schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
        plan=plan,
        source=CleanupDatabaseIdentity(host="db", port=5432, database="sig_v2"),
        target=CleanupDatabaseIdentity(
            host="db",
            port=5432,
            database="sig_v2_cleanup_test",
            isolation_marker=REQUIRED_ISOLATION_MARKER,
        ),
        confirmation=CleanupExecutionConfirmation(
            run_id=RUN_ID,
            target_database="sig_v2_cleanup_test",
            commit_sha=COMMIT_SHA,
            plan_sha256=checksum,
            confirmation=confirmation_text,
        ),
    )


@dataclass
class _FakeResult:
    scalar: Any = None
    rowcount: int = -1

    def scalar_one(self) -> Any:
        return self.scalar


class _FakeTransaction:
    def __init__(self, connection: "_FakeConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "_FakeTransaction":
        self.connection.in_transaction = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self.connection.in_transaction = False
        if exc_type is None:
            self.connection.committed = True
        else:
            self.connection.rolled_back = True
        return False


class _FakeConnection:
    def __init__(
        self,
        *,
        counts: dict[str, list[int]],
        lock_acquired: bool = True,
        delete_rowcounts: dict[str, int] | None = None,
    ) -> None:
        self.counts = {table: list(values) for table, values in counts.items()}
        self.lock_acquired = lock_acquired
        self.delete_rowcounts = delete_rowcounts or {}
        self.statements: list[str] = []
        self.committed = False
        self.rolled_back = False
        self.in_transaction = False

    def begin(self) -> _FakeTransaction:
        return _FakeTransaction(self)

    def execute(self, statement: object, parameters: object = None) -> _FakeResult:
        sql = str(statement)
        self.statements.append(sql)
        if sql.startswith("SELECT pg_try_advisory_xact_lock"):
            return _FakeResult(scalar=self.lock_acquired)
        if sql.startswith("SELECT count(*) FROM"):
            table = sql.split('"')[1]
            return _FakeResult(scalar=self.counts[table].pop(0))
        if sql.startswith("DELETE FROM"):
            table = sql.split('"')[1]
            return _FakeResult(rowcount=self.delete_rowcounts.get(table, 0))
        raise AssertionError(f"unexpected SQL: {sql}")


def test_executor_validates_all_counts_before_first_delete_and_commits() -> None:
    payload = _plan_payload()
    connection = _FakeConnection(
        counts={"asset_prices": [2, 0], "transactions": [1, 0]},
        delete_rowcounts={"asset_prices": 2, "transactions": 1},
    )

    result = execute_isolated_cleanup(
        connection=connection,  # type: ignore[arg-type]
        authorization=_authorization(payload),
        plan_payload=payload,
    )

    first_delete = next(
        position for position, sql in enumerate(connection.statements) if sql.startswith("DELETE")
    )
    count_positions = [
        position
        for position, sql in enumerate(connection.statements)
        if sql.startswith("SELECT count(*)")
    ]
    assert count_positions[:2] == [1, 2]
    assert first_delete == 3
    assert connection.committed is True
    assert connection.rolled_back is False
    assert result.rows_before == 3
    assert result.rows_deleted == 3
    assert [table.table_name for table in result.tables] == payload["cleanup_order"]


def test_executor_aborts_before_first_write_on_count_mismatch() -> None:
    payload = _plan_payload()
    connection = _FakeConnection(
        counts={"asset_prices": [2], "transactions": [9]},
    )

    with pytest.raises(IsolatedCleanupCountMismatchError, match="transactions"):
        execute_isolated_cleanup(
            connection=connection,  # type: ignore[arg-type]
            authorization=_authorization(payload),
            plan_payload=payload,
        )

    assert not any(sql.startswith("DELETE") for sql in connection.statements)
    assert connection.rolled_back is True


def test_executor_aborts_when_operational_lock_is_unavailable() -> None:
    payload = _plan_payload()
    connection = _FakeConnection(counts={}, lock_acquired=False)

    with pytest.raises(IsolatedCleanupLockUnavailableError, match="lock"):
        execute_isolated_cleanup(
            connection=connection,  # type: ignore[arg-type]
            authorization=_authorization(payload),
            plan_payload=payload,
        )

    assert connection.statements == ["SELECT pg_try_advisory_xact_lock(:lock_key)"]
    assert connection.rolled_back is True


def test_executor_rolls_back_when_postcondition_fails() -> None:
    payload = _plan_payload()
    connection = _FakeConnection(
        counts={"asset_prices": [2, 1], "transactions": [1]},
        delete_rowcounts={"asset_prices": 1},
    )

    with pytest.raises(IsolatedCleanupPostconditionError, match="asset_prices"):
        execute_isolated_cleanup(
            connection=connection,  # type: ignore[arg-type]
            authorization=_authorization(payload),
            plan_payload=payload,
        )

    assert connection.committed is False
    assert connection.rolled_back is True
    assert not any('"transactions"' in sql and sql.startswith("DELETE") for sql in connection.statements)


def test_executor_rolls_back_on_controlled_rehearsal_failure() -> None:
    payload = _plan_payload()
    connection = _FakeConnection(
        counts={"asset_prices": [2, 0], "transactions": [1]},
        delete_rowcounts={"asset_prices": 2},
    )

    def fail_after_first_table(table_name: str) -> None:
        assert table_name == "asset_prices"
        raise IsolatedCleanupExecutionError("controlled rehearsal failure")

    with pytest.raises(IsolatedCleanupExecutionError, match="controlled"):
        execute_isolated_cleanup(
            connection=connection,  # type: ignore[arg-type]
            authorization=_authorization(payload),
            plan_payload=payload,
            after_table_cleanup=fail_after_first_table,
        )

    assert connection.committed is False
    assert connection.rolled_back is True
    assert not any(
        sql.startswith("DELETE") and '"transactions"' in sql
        for sql in connection.statements
    )


def test_executor_rejects_table_list_that_differs_from_cleanup_order() -> None:
    payload = _plan_payload()
    payload["tables"] = list(reversed(payload["tables"]))
    authorization = _authorization(payload)
    connection = _FakeConnection(counts={})

    with pytest.raises(Exception, match="match cleanup_order"):
        execute_isolated_cleanup(
            connection=connection,  # type: ignore[arg-type]
            authorization=authorization,
            plan_payload=payload,
        )

    assert connection.statements == []


def test_executor_rejects_unsafe_identifier_without_delete() -> None:
    payload = _plan_payload()
    payload["cleanup_order"] = ["asset_prices; DROP TABLE users", "transactions"]
    payload["tables"][0]["name"] = "asset_prices; DROP TABLE users"
    authorization = _authorization(payload)
    connection = _FakeConnection(counts={})

    with pytest.raises(IsolatedCleanupExecutionError, match="unsafe"):
        execute_isolated_cleanup(
            connection=connection,  # type: ignore[arg-type]
            authorization=authorization,
            plan_payload=payload,
        )

    assert not any(sql.startswith("DELETE") for sql in connection.statements)
    assert connection.rolled_back is True
