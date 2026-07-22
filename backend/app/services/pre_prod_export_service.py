"""Serviço de exportação auditável dos dados não reconstruíveis.

A origem é lida em um único snapshot PostgreSQL REPEATABLE READ READ ONLY. Os
artefatos são construídos em diretório temporário e publicados por rename
atômico, sem sobrescrever execuções anteriores.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncIterator, Mapping, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_cleanup_impact_contract import PreProdCleanupImpactReport
from app.services.pre_prod_export_contract import (
    EXPORT_CLASSIFICATION,
    EXPORT_FORMAT,
    EXPORT_MANIFEST_SCHEMA_VERSION,
    ExportColumn,
    ExportSafety,
    ExportSourceSnapshot,
    ExportTableArtifact,
    PreProdExportManifest,
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class ExportPaths:
    final_directory: Path
    temporary_directory: Path


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quote_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"unsafe PostgreSQL identifier: {identifier!r}")
    return f'"{identifier}"'


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    if isinstance(value, bytes):
        return "\\x" + value.hex()
    return value


def _prepare_paths(output_root: Path, run_id: str) -> ExportPaths:
    if not run_id.strip() or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be a safe directory name")
    final_directory = output_root / run_id / "export"
    temporary_directory = output_root / run_id / ".export.tmp"
    if final_directory.exists() or temporary_directory.exists():
        raise FileExistsError(f"export artifacts already exist for run_id {run_id!r}")
    temporary_directory.mkdir(parents=True, exist_ok=False)
    return ExportPaths(
        final_directory=final_directory,
        temporary_directory=temporary_directory,
    )


def _validate_gate(report: PreProdCleanupImpactReport) -> list[str]:
    if not report.ok:
        raise ValueError("cleanup impact gate is not approved")
    tables = sorted(report.dependency_plan.export_required_before_cleanup)
    classified = sorted(
        table.name
        for table in report.tables
        if table.classification == EXPORT_CLASSIFICATION
    )
    if not tables or tables != classified:
        raise ValueError("cleanup impact export gate is inconsistent")
    return tables


async def _read_columns(
    session: AsyncSession,
    table_name: str,
) -> list[ExportColumn]:
    result = await session.execute(
        text(
            """
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable,
                ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table_name
            ORDER BY ordinal_position
            """
        ),
        {"table_name": table_name},
    )
    rows = list(result)
    columns = [
        ExportColumn(
            name=row.column_name,
            postgres_type=(
                row.udt_name if row.data_type == "USER-DEFINED" else row.data_type
            ),
            nullable=row.is_nullable == "YES",
            ordinal_position=export_ordinal,
        )
        for export_ordinal, row in enumerate(rows, start=1)
    ]
    if not columns:
        raise ValueError(f"export table not found in public schema: {table_name!r}")
    return columns


async def _stream_rows(
    session: AsyncSession,
    table_name: str,
    columns: Sequence[ExportColumn],
) -> AsyncIterator[Sequence[Any]]:
    projection = ", ".join(_quote_identifier(column.name) for column in columns)
    statement = text(f"SELECT {projection} FROM {_quote_identifier(table_name)}")
    result = await session.stream(statement)
    async for row in result:
        yield tuple(row)


async def _write_table_csv(
    *,
    session: AsyncSession,
    table_name: str,
    columns: list[ExportColumn],
    destination: Path,
) -> int:
    row_count = 0
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([column.name for column in columns])
        async for row in _stream_rows(session, table_name, columns):
            writer.writerow([_csv_value(value) for value in row])
            row_count += 1
        handle.flush()
        os.fsync(handle.fileno())
    return row_count


async def build_pre_prod_export(
    *,
    cleanup_impact: PreProdCleanupImpactReport,
    branch: str,
    commit_sha: str,
    run_id: str,
    generated_at: str,
    output_root: Path,
    session: AsyncSession | None = None,
    transaction_started: bool = False,
) -> PreProdExportManifest:
    """Exporta exatamente as tabelas aprovadas pelo gate e publica o manifesto.

    ``transaction_started`` só deve ser usado quando o chamador já abriu a
    transação REPEATABLE READ READ ONLY compartilhada com o cleanup impact.
    """
    if transaction_started and session is None:
        raise ValueError("transaction_started requires a supplied session")

    export_tables = _validate_gate(cleanup_impact)
    cleanup_payload = cleanup_impact.to_dict()
    cleanup_sha256 = _sha256_bytes(_canonical_json_bytes(cleanup_payload))
    paths = _prepare_paths(output_root, run_id)
    owns_session = session is None
    active_session = session or AsyncSessionLocal()

    try:
        if not transaction_started:
            await active_session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
        artifacts: list[ExportTableArtifact] = []
        for table_name in export_tables:
            columns = await _read_columns(active_session, table_name)
            relative_path = f"tables/{table_name}.csv"
            destination = paths.temporary_directory / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            row_count = await _write_table_csv(
                session=active_session,
                table_name=table_name,
                columns=columns,
                destination=destination,
            )
            schema_payload = {
                "table_name": table_name,
                "columns": [
                    {
                        "name": column.name,
                        "postgres_type": column.postgres_type,
                        "nullable": column.nullable,
                        "ordinal_position": column.ordinal_position,
                    }
                    for column in columns
                ],
            }
            artifacts.append(
                ExportTableArtifact(
                    table_name=table_name,
                    classification=EXPORT_CLASSIFICATION,
                    row_count=row_count,
                    relative_path=relative_path,
                    format=EXPORT_FORMAT,
                    byte_size=destination.stat().st_size,
                    data_sha256=_sha256_file(destination),
                    schema_sha256=_sha256_bytes(
                        _canonical_json_bytes(schema_payload)
                    ),
                    columns=columns,
                )
            )

        manifest = PreProdExportManifest(
            schema_version=EXPORT_MANIFEST_SCHEMA_VERSION,
            generated_at=generated_at,
            run_id=run_id,
            branch=branch,
            commit_sha=commit_sha,
            source=ExportSourceSnapshot(
                transaction_isolation="repeatable read",
                read_only=True,
                cleanup_impact_schema_version=cleanup_impact.schema_version,
                cleanup_impact_sha256=cleanup_sha256,
                inventory_schema_version=cleanup_impact.inventory_schema_version,
                exported_tables=export_tables,
            ),
            tables=artifacts,
            safety=ExportSafety(),
        )
        manifest_path = paths.temporary_directory / "manifest.json"
        manifest_path.write_bytes(
            json.dumps(
                manifest.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
        paths.final_directory.parent.mkdir(parents=True, exist_ok=True)
        paths.temporary_directory.rename(paths.final_directory)
        return manifest
    except Exception:
        shutil.rmtree(paths.temporary_directory, ignore_errors=True)
        raise
    finally:
        await active_session.rollback()
        if owns_session:
            await active_session.close()
