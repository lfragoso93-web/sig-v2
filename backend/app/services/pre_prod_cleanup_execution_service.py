"""Valida artefatos aprovados e publica o plano de limpeza sem acessar o banco."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from app.services.pre_prod_cleanup_execution_contract import (
    CLEANUP_BRANCH,
    CLEANUP_EXECUTION_MODE,
    CLEANUP_EXECUTION_SCHEMA_VERSION,
    CleanupExecutionArtifact,
    CleanupExecutionSafety,
    CleanupExecutionTable,
    PreProdCleanupExecutionPlan,
)

CLEANUP_IMPACT_SCHEMA_VERSION = "pre-prod-cleanup-impact.v2"
EXPORT_MANIFEST_SCHEMA_VERSION = "pre-prod-export.v1"
DEFAULT_PLAN_FILENAME = "plan.json"
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class CleanupExecutionValidationError(RuntimeError):
    """Falha fechada ao validar a fundação da limpeza."""


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


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise CleanupExecutionValidationError(f"{label} não encontrado: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CleanupExecutionValidationError(f"{label} inválido: {path}") from exc
    if not isinstance(payload, dict):
        raise CleanupExecutionValidationError(f"{label} deve ser um objeto JSON")
    return payload


def _require_string(payload: Mapping[str, Any], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CleanupExecutionValidationError(f"{label}.{key} deve ser texto não vazio")
    return value


def _require_list(payload: Mapping[str, Any], key: str, label: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise CleanupExecutionValidationError(f"{label}.{key} deve ser lista")
    return value


def _validate_identity(
    *,
    cleanup_impact: Mapping[str, Any],
    manifest: Mapping[str, Any],
    run_id: str,
    branch: str,
    commit_sha: str,
) -> None:
    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise CleanupExecutionValidationError("run_id inseguro")
    if branch != CLEANUP_BRANCH:
        raise CleanupExecutionValidationError("branch deve ser stable-15jun")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise CleanupExecutionValidationError("commit_sha deve conter 40 hexadecimais")

    if _require_string(cleanup_impact, "schema_version", "cleanup_impact") != CLEANUP_IMPACT_SCHEMA_VERSION:
        raise CleanupExecutionValidationError("schema de cleanup impact não suportado")
    if cleanup_impact.get("ok") is not True:
        raise CleanupExecutionValidationError("cleanup impact não está aprovado")
    if cleanup_impact.get("blockers") not in ([], None):
        raise CleanupExecutionValidationError("cleanup impact contém blockers")

    if _require_string(manifest, "schema_version", "manifest") != EXPORT_MANIFEST_SCHEMA_VERSION:
        raise CleanupExecutionValidationError("schema de export manifest não suportado")
    if _require_string(manifest, "run_id", "manifest") != run_id:
        raise CleanupExecutionValidationError("run_id diverge do manifesto")
    if _require_string(manifest, "branch", "manifest") != branch:
        raise CleanupExecutionValidationError("branch diverge do manifesto")
    if _require_string(manifest, "commit_sha", "manifest").lower() != commit_sha.lower():
        raise CleanupExecutionValidationError("commit SHA diverge do manifesto")
    if _require_string(cleanup_impact, "branch", "cleanup_impact") != branch:
        raise CleanupExecutionValidationError("branch diverge do cleanup impact")
    if _require_string(cleanup_impact, "commit_sha", "cleanup_impact").lower() != commit_sha.lower():
        raise CleanupExecutionValidationError("commit SHA diverge do cleanup impact")


def _cleanup_tables(cleanup_impact: Mapping[str, Any]) -> tuple[list[CleanupExecutionTable], list[str]]:
    dependency_plan = cleanup_impact.get("dependency_plan")
    if not isinstance(dependency_plan, dict):
        raise CleanupExecutionValidationError("cleanup impact sem dependency_plan")
    cycles = dependency_plan.get("cycles")
    if cycles not in ([], None):
        raise CleanupExecutionValidationError("dependency plan contém ciclos")
    cleanup_order = _require_list(dependency_plan, "cleanup_order", "dependency_plan")
    if not cleanup_order or not all(isinstance(name, str) and name for name in cleanup_order):
        raise CleanupExecutionValidationError("cleanup_order deve conter tabelas")
    if len(cleanup_order) != len(set(cleanup_order)):
        raise CleanupExecutionValidationError("cleanup_order contém duplicatas")

    table_payloads = _require_list(cleanup_impact, "tables", "cleanup_impact")
    indexed: dict[str, Mapping[str, Any]] = {}
    for raw_table in table_payloads:
        if not isinstance(raw_table, dict):
            raise CleanupExecutionValidationError("tabela do cleanup impact inválida")
        name = _require_string(raw_table, "name", "cleanup_table")
        indexed[name] = raw_table

    tables: list[CleanupExecutionTable] = []
    for position, name in enumerate(cleanup_order, start=1):
        raw_table = indexed.get(name)
        if raw_table is None:
            raise CleanupExecutionValidationError(f"cleanup_order referencia tabela desconhecida: {name}")
        classification = raw_table.get("classification")
        if classification not in {"export_before_cleanup", "rebuildable"}:
            raise CleanupExecutionValidationError(f"classificação não limpável: {name}")
        row_count = raw_table.get("row_count")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
            raise CleanupExecutionValidationError(f"row_count inválido: {name}")
        tables.append(
            CleanupExecutionTable(
                name=name,
                classification=classification,
                expected_rows_before=row_count,
                cleanup_position=position,
            )
        )
    return tables, list(cleanup_order)


def _validate_export_artifacts(
    *,
    run_directory: Path,
    manifest_path: Path,
    cleanup_impact_path: Path,
    cleanup_impact: Mapping[str, Any],
    manifest: Mapping[str, Any],
    tables: list[CleanupExecutionTable],
) -> tuple[list[CleanupExecutionArtifact], str, str]:
    cleanup_sha256 = _sha256_bytes(_canonical_json_bytes(cleanup_impact))
    manifest_sha256 = _sha256_file(manifest_path)

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise CleanupExecutionValidationError("manifest sem source")
    if source.get("cleanup_impact_schema_version") != CLEANUP_IMPACT_SCHEMA_VERSION:
        raise CleanupExecutionValidationError("manifest referencia schema de impacto divergente")
    if source.get("cleanup_impact_sha256") != cleanup_sha256:
        raise CleanupExecutionValidationError("checksum do cleanup impact diverge do manifesto")

    manifest_tables = _require_list(manifest, "tables", "manifest")
    artifacts = [
        CleanupExecutionArtifact(
            kind="cleanup_impact",
            schema_version=CLEANUP_IMPACT_SCHEMA_VERSION,
            relative_path=cleanup_impact_path.relative_to(run_directory).as_posix(),
            sha256=cleanup_sha256,
        ),
        CleanupExecutionArtifact(
            kind="export_manifest",
            schema_version=EXPORT_MANIFEST_SCHEMA_VERSION,
            relative_path=manifest_path.relative_to(run_directory).as_posix(),
            sha256=manifest_sha256,
        ),
    ]

    exported_names: set[str] = set()
    for raw_table in manifest_tables:
        if not isinstance(raw_table, dict):
            raise CleanupExecutionValidationError("tabela do manifesto inválida")
        table_name = _require_string(raw_table, "table_name", "manifest_table")
        relative_path = _require_string(raw_table, "relative_path", "manifest_table")
        data_sha256 = _require_string(raw_table, "data_sha256", "manifest_table")
        artifact_path = manifest_path.parent / relative_path
        try:
            artifact_relative = artifact_path.relative_to(run_directory).as_posix()
        except ValueError as exc:
            raise CleanupExecutionValidationError("artefato exportado fora do run_directory") from exc
        if not artifact_path.is_file():
            raise CleanupExecutionValidationError(f"CSV exportado não encontrado: {table_name}")
        if _sha256_file(artifact_path) != data_sha256:
            raise CleanupExecutionValidationError(f"checksum do CSV diverge: {table_name}")
        exported_names.add(table_name)
        artifacts.append(
            CleanupExecutionArtifact(
                kind="export_table",
                schema_version="csv",
                relative_path=artifact_relative,
                sha256=data_sha256,
            )
        )

    expected_exported = {
        table.name for table in tables if table.classification == "export_before_cleanup"
    }
    source_exported = source.get("exported_tables")
    if not isinstance(source_exported, list) or set(source_exported) != expected_exported:
        raise CleanupExecutionValidationError("gate de exportação diverge do cleanup impact")
    if exported_names != expected_exported:
        raise CleanupExecutionValidationError("manifesto não contém exatamente as tabelas exportáveis")
    return artifacts, cleanup_sha256, manifest_sha256


def build_pre_prod_cleanup_execution_plan(
    *,
    run_directory: Path,
    cleanup_impact_path: Path,
    manifest_path: Path,
    run_id: str,
    branch: str,
    commit_sha: str,
    generated_at: str,
) -> PreProdCleanupExecutionPlan:
    """Monta o plano somente após validar integralmente os artefatos em disco."""
    run_directory = run_directory.resolve()
    cleanup_impact_path = cleanup_impact_path.resolve()
    manifest_path = manifest_path.resolve()
    for path, label in (
        (cleanup_impact_path, "cleanup impact"),
        (manifest_path, "export manifest"),
    ):
        try:
            path.relative_to(run_directory)
        except ValueError as exc:
            raise CleanupExecutionValidationError(f"{label} fora do run_directory") from exc

    cleanup_impact = _load_json_object(cleanup_impact_path, "cleanup impact")
    manifest = _load_json_object(manifest_path, "export manifest")
    _validate_identity(
        cleanup_impact=cleanup_impact,
        manifest=manifest,
        run_id=run_id,
        branch=branch,
        commit_sha=commit_sha,
    )
    tables, cleanup_order = _cleanup_tables(cleanup_impact)
    artifacts, cleanup_sha256, manifest_sha256 = _validate_export_artifacts(
        run_directory=run_directory,
        manifest_path=manifest_path,
        cleanup_impact_path=cleanup_impact_path,
        cleanup_impact=cleanup_impact,
        manifest=manifest,
        tables=tables,
    )
    return PreProdCleanupExecutionPlan(
        schema_version=CLEANUP_EXECUTION_SCHEMA_VERSION,
        generated_at=generated_at,
        mode=CLEANUP_EXECUTION_MODE,
        run_id=run_id,
        branch=branch,
        commit_sha=commit_sha.lower(),
        cleanup_impact_sha256=cleanup_sha256,
        export_manifest_sha256=manifest_sha256,
        artifacts=artifacts,
        tables=tables,
        cleanup_order=cleanup_order,
        blockers=[],
        safety=CleanupExecutionSafety(),
    )


def publish_pre_prod_cleanup_execution_plan(
    *,
    plan: PreProdCleanupExecutionPlan,
    run_directory: Path,
    filename: str = DEFAULT_PLAN_FILENAME,
) -> Path:
    """Publica JSON por rename atômico e recusa qualquer sobrescrita."""
    destination_directory = run_directory / "cleanup"
    destination = destination_directory / filename
    temporary = destination_directory / f".{filename}.tmp"
    if destination.exists() or temporary.exists():
        raise FileExistsError(f"cleanup execution plan already exists for {plan.run_id!r}")
    destination_directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination
