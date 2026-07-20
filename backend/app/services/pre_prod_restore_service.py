"""Restauração isolada e reconciliação do backup pré-produção."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Callable
from urllib.parse import unquote, urlsplit

from app.services.pre_prod_backup_service import (
    BackupError,
    CommandResult,
    run_checked,
    sha256_file,
    write_json,
)


RESTORE_REPORT_SCHEMA_VERSION = "pre-prod-restore.v1"
RECONCILIATION_SCHEMA_VERSION = "pre-prod-reconciliation.v1"
Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class DatabaseIdentity:
    host: str
    port: int
    database: str


@dataclass(frozen=True)
class RestoreExecution:
    dump_file: str
    sha256: str
    target: DatabaseIdentity
    commands: list[CommandResult]


@dataclass(frozen=True)
class ReconciliationReport:
    schema_version: str
    generated_at: str
    ok: bool
    source_inventory_schema: str | None
    restored_inventory_schema: str | None
    source_migrations: list[str]
    restored_migrations: list[str]
    missing_tables: list[str]
    unexpected_tables: list[str]
    classification_mismatches: list[dict[str, object]]
    row_count_mismatches: list[dict[str, object]]
    finding_mismatches: list[dict[str, object]]
    safety: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def database_identity(database_url: str) -> DatabaseIdentity:
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise BackupError("pre_prod_restore aceita somente URLs PostgreSQL síncronas")
    database = unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or not database:
        raise BackupError("URL PostgreSQL deve informar host e banco")
    return DatabaseIdentity(
        host=parsed.hostname.lower(),
        port=parsed.port or 5432,
        database=database,
    )


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError(f"artefato JSON inválido: {path}") from exc
    if not isinstance(payload, dict):
        raise BackupError(f"artefato JSON deve conter um objeto: {path}")
    return payload


def _query_to_file(
    *,
    database_url: str,
    sql: str,
    output_path: Path,
    runner: Runner,
) -> CommandResult:
    return run_checked(
        [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--set",
            "ON_ERROR_STOP=1",
            "--dbname",
            database_url,
            "--command",
            sql,
        ],
        runner=runner,
        stdout_path=output_path,
    )


def restore_postgres_backup(
    *,
    artifact_directory: Path,
    source_database_url: str,
    target_database_url: str,
    runner: Runner = subprocess.run,
) -> RestoreExecution:
    """Valida o artefato e restaura somente em um banco diferente e vazio."""
    source = database_identity(source_database_url)
    target = database_identity(target_database_url)
    if source == target:
        raise BackupError("o banco de restauração não pode ser a origem")
    if source.database == target.database:
        raise BackupError("origem e destino devem usar nomes de banco diferentes")

    dump_path = artifact_directory / "database.dump"
    report_path = artifact_directory / "backup-report.json"
    if not dump_path.is_file() or dump_path.stat().st_size == 0:
        raise BackupError("database.dump ausente ou vazio")
    backup_report = _load_json(report_path)
    expected_checksum = backup_report.get("sha256")
    actual_checksum = sha256_file(dump_path)
    if expected_checksum != actual_checksum:
        raise BackupError("checksum SHA-256 do dump diverge do manifesto")

    preflight_path = artifact_directory / "restore-target-preflight.txt"
    commands = [
        _query_to_file(
            database_url=target_database_url,
            sql=(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ),
            output_path=preflight_path,
            runner=runner,
        )
    ]
    try:
        existing_tables = int(preflight_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise BackupError("não foi possível validar se o banco isolado está vazio") from exc
    if existing_tables != 0:
        raise BackupError(
            f"banco isolado deve estar vazio; tabelas encontradas: {existing_tables}"
        )

    commands.append(
        run_checked(
            [
                "pg_restore",
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                target_database_url,
                str(dump_path),
            ],
            runner=runner,
        )
    )
    return RestoreExecution(
        dump_file=dump_path.name,
        sha256=actual_checksum,
        target=target,
        commands=commands,
    )


def read_migration_versions(
    *,
    database_url: str,
    output_path: Path,
    runner: Runner = subprocess.run,
) -> tuple[list[str], CommandResult]:
    command = _query_to_file(
        database_url=database_url,
        sql="SELECT version_num FROM alembic_version ORDER BY version_num",
        output_path=output_path,
        runner=runner,
    )
    versions = [
        line.strip()
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return versions, command


def reconcile_inventories(
    *,
    source_inventory: dict[str, object],
    restored_inventory: dict[str, object],
    source_migrations: list[str],
    restored_migrations: list[str],
) -> ReconciliationReport:
    def object_list(
        payload: dict[str, object],
        key: str,
    ) -> list[dict[str, object]]:
        value = payload.get(key)
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def total(payload: dict[str, object], key: str, default: int) -> object:
        totals = payload.get("totals")
        if not isinstance(totals, dict):
            return default
        return totals.get(key, default)

    source_tables = {
        str(item["name"]): item
        for item in object_list(source_inventory, "tables")
        if "name" in item
    }
    restored_tables = {
        str(item["name"]): item
        for item in object_list(restored_inventory, "tables")
        if "name" in item
    }
    shared_names = sorted(source_tables.keys() & restored_tables.keys())
    classification_mismatches = [
        {
            "table": name,
            "source": source_tables[name].get("classification"),
            "restored": restored_tables[name].get("classification"),
        }
        for name in shared_names
        if source_tables[name].get("classification")
        != restored_tables[name].get("classification")
    ]
    row_count_mismatches = [
        {
            "table": name,
            "source": source_tables[name].get("row_count"),
            "restored": restored_tables[name].get("row_count"),
        }
        for name in shared_names
        if source_tables[name].get("row_count")
        != restored_tables[name].get("row_count")
    ]

    def findings(payload: dict[str, object]) -> dict[str, tuple[object, object]]:
        return {
            str(item["code"]): (item.get("severity"), item.get("count"))
            for item in object_list(payload, "findings")
            if "code" in item
        }

    source_findings = findings(source_inventory)
    restored_findings = findings(restored_inventory)
    finding_mismatches = [
        {
            "finding": code,
            "source": source_findings.get(code),
            "restored": restored_findings.get(code),
        }
        for code in sorted(source_findings.keys() | restored_findings.keys())
        if source_findings.get(code) != restored_findings.get(code)
    ]
    missing_tables = sorted(source_tables.keys() - restored_tables.keys())
    unexpected_tables = sorted(restored_tables.keys() - source_tables.keys())
    source_schema = source_inventory.get("schema_version")
    restored_schema = restored_inventory.get("schema_version")
    ok = not any(
        (
            source_schema != "pre-prod-inventory.v2",
            restored_schema != "pre-prod-inventory.v2",
            source_migrations != restored_migrations,
            missing_tables,
            unexpected_tables,
            classification_mismatches,
            row_count_mismatches,
            finding_mismatches,
            total(restored_inventory, "unclassified_tables", 1),
            total(restored_inventory, "blocking_findings", 1),
        )
    )
    return ReconciliationReport(
        schema_version=RECONCILIATION_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        ok=ok,
        source_inventory_schema=(str(source_schema) if source_schema else None),
        restored_inventory_schema=(str(restored_schema) if restored_schema else None),
        source_migrations=source_migrations,
        restored_migrations=restored_migrations,
        missing_tables=missing_tables,
        unexpected_tables=unexpected_tables,
        classification_mismatches=classification_mismatches,
        row_count_mismatches=row_count_mismatches,
        finding_mismatches=finding_mismatches,
        safety={
            "source_database_writes_executed": 0,
            "restore_target_only": True,
            "cleanup_executed": False,
            "rebuild_executed": False,
        },
    )


def write_restore_report(
    *,
    artifact_directory: Path,
    execution: RestoreExecution,
    reconciliation: ReconciliationReport,
    migration_commands: list[CommandResult],
) -> None:
    write_json(
        artifact_directory / "restore-report.json",
        {
            "schema_version": RESTORE_REPORT_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dump_file": execution.dump_file,
            "sha256": execution.sha256,
            "target": asdict(execution.target),
            "commands": [
                asdict(command)
                for command in [*execution.commands, *migration_commands]
            ],
            "reconciliation_file": "reconciliation-report.json",
            "ok": reconciliation.ok,
            "safety": reconciliation.safety,
        },
    )
    write_json(
        artifact_directory / "reconciliation-report.json",
        reconciliation.to_dict(),
    )
