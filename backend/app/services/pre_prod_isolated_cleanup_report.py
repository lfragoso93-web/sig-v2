"""Relatório auditável da limpeza controlada em PostgreSQL isolado.

Este módulo transforma o resultado transacional em um artefato UTF-8, redigido,
publicado de forma atômica e sem sobrescrever uma execução anterior.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from app.services.pre_prod_isolated_cleanup_contract import (
    APPROVED_BRANCH,
    ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
    IsolatedCleanupAuthorization,
)
from app.services.pre_prod_isolated_cleanup_executor import (
    IsolatedCleanupExecutionResult,
)

DEFAULT_ARTIFACT_ROOT = Path("artifacts/pre-prod-rebuild")
EXECUTION_REPORT_NAME = "execution.json"


class IsolatedCleanupReportError(RuntimeError):
    """Falha ao construir ou publicar o relatório de execução."""


class IsolatedCleanupReportAlreadyExistsError(IsolatedCleanupReportError):
    """O artefato final já existe e nunca deve ser sobrescrito."""


@dataclass(frozen=True)
class IsolatedCleanupExecutionReport:
    schema_version: str
    run_id: str
    branch: str
    commit_sha: str
    target_database: str
    plan_sha256: str
    started_at: str
    finished_at: str
    final_state: str
    lock_acquired: bool
    committed: bool
    preserved_tables_unchanged: bool
    rebuild_started: bool
    cleanup_order: tuple[str, ...]
    tables: tuple[Mapping[str, Any], ...]
    totals: Mapping[str, int]
    abort_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_execution_report(
    *,
    authorization: IsolatedCleanupAuthorization,
    result: IsolatedCleanupExecutionResult,
    started_at: str,
    finished_at: str,
) -> IsolatedCleanupExecutionReport:
    """Constrói o relatório de sucesso sem expor URL ou credenciais."""
    if result.run_id != authorization.plan.run_id:
        raise IsolatedCleanupReportError("execution result run_id differs from authorization")
    if result.plan_sha256 != authorization.plan.plan_sha256:
        raise IsolatedCleanupReportError(
            "execution result plan checksum differs from authorization"
        )
    if result.target_database != authorization.target.redacted_label:
        raise IsolatedCleanupReportError(
            "execution result target differs from redacted authorized target"
        )
    if not result.committed:
        raise IsolatedCleanupReportError(
            "successful execution report requires a committed result"
        )

    table_payloads = tuple(asdict(table) for table in result.tables)
    return IsolatedCleanupExecutionReport(
        schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
        run_id=authorization.plan.run_id,
        branch=APPROVED_BRANCH,
        commit_sha=authorization.plan.commit_sha,
        target_database=authorization.target.redacted_label,
        plan_sha256=authorization.plan.plan_sha256,
        started_at=started_at,
        finished_at=finished_at,
        final_state="committed",
        lock_acquired=result.lock_acquired,
        committed=True,
        preserved_tables_unchanged=True,
        rebuild_started=False,
        cleanup_order=authorization.plan.cleanup_order,
        tables=table_payloads,
        totals={
            "tables": len(result.tables),
            "rows_before": result.rows_before,
            "rows_deleted": result.rows_deleted,
            "rows_after": sum(table.actual_rows_after for table in result.tables),
            "database_writes": result.rows_deleted,
        },
    )


def execution_report_path(
    *,
    run_id: str,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
) -> Path:
    if not run_id.strip() or "/" in run_id or "\\" in run_id:
        raise IsolatedCleanupReportError("run_id must be a safe non-empty name")
    return artifact_root / run_id / "cleanup" / EXECUTION_REPORT_NAME


def publish_execution_report(
    *,
    report: IsolatedCleanupExecutionReport,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
) -> Path:
    """Publica JSON por hard-link atômico, recusando sobrescrita.

    O arquivo temporário é gravado e sincronizado no mesmo diretório. ``os.link``
    cria o destino somente se ele ainda não existir; assim não há janela de
    substituição silenciosa de evidência anterior.
    """
    destination = execution_report_path(
        run_id=report.run_id,
        artifact_root=artifact_root,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{uuid4().hex}.tmp"
    )
    payload = json.dumps(
        report.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise IsolatedCleanupReportAlreadyExistsError(
                f"execution report already exists: {destination}"
            ) from exc
        return destination
    finally:
        temporary.unlink(missing_ok=True)
