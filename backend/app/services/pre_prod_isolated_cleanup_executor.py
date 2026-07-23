"""Executor transacional da limpeza controlada em PostgreSQL isolado.

O executor consome exclusivamente o plano aprovado e a autorização validada. Ele
não lê arquivos, variáveis de ambiente ou credenciais, não publica artefatos e
não inicia rebuild. Toda escrita ocorre em uma única transação e somente nas
tabelas presentes em ``cleanup_order``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Mapping, Protocol

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.services.pre_prod_isolated_cleanup_contract import (
    IsolatedCleanupAuthorization,
    IsolatedCleanupValidationError,
    validate_approved_plan,
)

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LOCK_NAMESPACE = "sgi-v2:pre-prod-isolated-cleanup"


class IsolatedCleanupExecutionError(RuntimeError):
    """Falha fechada durante a execução transacional."""


class IsolatedCleanupLockUnavailableError(IsolatedCleanupExecutionError):
    """Outro processo já mantém o lock operacional do cleanup."""


class IsolatedCleanupCountMismatchError(IsolatedCleanupExecutionError):
    """A contagem atual diverge do plano aprovado."""


class IsolatedCleanupPostconditionError(IsolatedCleanupExecutionError):
    """Uma tabela não ficou vazia após sua operação de limpeza."""


@dataclass(frozen=True)
class CleanupTableExecution:
    table_name: str
    expected_rows_before: int
    actual_rows_before: int
    deleted_rows: int
    actual_rows_after: int


@dataclass(frozen=True)
class IsolatedCleanupExecutionResult:
    run_id: str
    target_database: str
    plan_sha256: str
    lock_acquired: bool
    committed: bool
    tables: tuple[CleanupTableExecution, ...]

    @property
    def rows_before(self) -> int:
        return sum(table.actual_rows_before for table in self.tables)

    @property
    def rows_deleted(self) -> int:
        return sum(table.deleted_rows for table in self.tables)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["totals"] = {
            "tables": len(self.tables),
            "rows_before": self.rows_before,
            "rows_deleted": self.rows_deleted,
            "rows_after": sum(table.actual_rows_after for table in self.tables),
        }
        return payload


def _quote_identifier(value: str) -> str:
    if not _SAFE_IDENTIFIER.fullmatch(value):
        raise IsolatedCleanupExecutionError(f"unsafe cleanup table identifier: {value!r}")
    return f'"{value}"'


def _advisory_lock_key(run_id: str, target_database: str) -> int:
    material = f"{_LOCK_NAMESPACE}:{run_id}:{target_database}".encode("utf-8")
    unsigned = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return unsigned if unsigned < 2**63 else unsigned - 2**64


def _expected_rows_by_table(
    payload: Mapping[str, Any], cleanup_order: tuple[str, ...]
) -> dict[str, int]:
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list):
        raise IsolatedCleanupValidationError("cleanup plan tables must be a list")

    expected: dict[str, int] = {}
    for raw_table in raw_tables:
        if not isinstance(raw_table, Mapping):
            raise IsolatedCleanupValidationError("cleanup plan table entry must be an object")
        name = raw_table.get("name")
        rows = raw_table.get("expected_rows_before")
        if not isinstance(name, str) or not name.strip():
            raise IsolatedCleanupValidationError("cleanup plan table name is required")
        if (
            not isinstance(rows, int)
            or isinstance(rows, bool)
            or rows < 0
        ):
            raise IsolatedCleanupValidationError(
                f"invalid expected_rows_before for cleanup table {name!r}"
            )
        if name in expected:
            raise IsolatedCleanupValidationError(f"duplicate cleanup table: {name}")
        expected[name] = rows

    if tuple(expected) != cleanup_order:
        raise IsolatedCleanupValidationError(
            "cleanup plan tables must match cleanup_order exactly and in order"
        )
    return expected


def _scalar_count(connection: Connection, table_name: str) -> int:
    quoted = _quote_identifier(table_name)
    value = connection.execute(text(f"SELECT count(*) FROM {quoted}")).scalar_one()
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise IsolatedCleanupExecutionError(
            f"database returned invalid row count for {table_name!r}"
        )
    return value


def execute_isolated_cleanup(
    *,
    connection: Connection,
    authorization: IsolatedCleanupAuthorization,
    plan_payload: Mapping[str, Any],
) -> IsolatedCleanupExecutionResult:
    """Executa o plano em transação única ou falha com rollback integral.

    Todas as contagens são verificadas antes do primeiro ``DELETE``. A ordem de
    execução vem exclusivamente do plano validado. Qualquer exceção deixa o
    rollback a cargo do contexto transacional do SQLAlchemy.
    """
    plan = validate_approved_plan(
        payload=plan_payload,
        expected_run_id=authorization.plan.run_id,
        expected_commit_sha=authorization.plan.commit_sha,
        expected_plan_sha256=authorization.plan.plan_sha256,
    )
    if plan != authorization.plan:
        raise IsolatedCleanupValidationError(
            "revalidated cleanup plan differs from authorized plan"
        )

    expected_rows = _expected_rows_by_table(plan_payload, plan.cleanup_order)
    lock_key = _advisory_lock_key(plan.run_id, authorization.target.database)

    table_results: list[CleanupTableExecution] = []
    with connection.begin():
        lock_acquired = connection.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        ).scalar_one()
        if lock_acquired is not True:
            raise IsolatedCleanupLockUnavailableError(
                "isolated cleanup operational lock is unavailable"
            )

        counts_before: dict[str, int] = {}
        for table_name in plan.cleanup_order:
            actual_rows = _scalar_count(connection, table_name)
            counts_before[table_name] = actual_rows
            expected = expected_rows[table_name]
            if actual_rows != expected:
                raise IsolatedCleanupCountMismatchError(
                    f"row count mismatch for {table_name}: expected {expected}, got {actual_rows}"
                )

        for table_name in plan.cleanup_order:
            quoted = _quote_identifier(table_name)
            delete_result = connection.execute(text(f"DELETE FROM {quoted}"))
            deleted_rows = delete_result.rowcount
            if not isinstance(deleted_rows, int) or deleted_rows < 0:
                raise IsolatedCleanupExecutionError(
                    f"database did not report deleted rows for {table_name!r}"
                )
            actual_rows_after = _scalar_count(connection, table_name)
            if actual_rows_after != 0:
                raise IsolatedCleanupPostconditionError(
                    f"cleanup postcondition failed for {table_name}: {actual_rows_after} rows remain"
                )
            table_results.append(
                CleanupTableExecution(
                    table_name=table_name,
                    expected_rows_before=expected_rows[table_name],
                    actual_rows_before=counts_before[table_name],
                    deleted_rows=deleted_rows,
                    actual_rows_after=actual_rows_after,
                )
            )

    return IsolatedCleanupExecutionResult(
        run_id=plan.run_id,
        target_database=authorization.target.redacted_label,
        plan_sha256=plan.plan_sha256,
        lock_acquired=True,
        committed=True,
        tables=tuple(table_results),
    )
