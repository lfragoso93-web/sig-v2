"""Verificacao independente de artefatos de dry-run corporativo."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


def verify_corporate_event_report_manifest(
    report_file: Path,
    manifest_file: Path,
) -> dict[str, Any]:
    """Valida hash, schema e invariantes read-only sem acessar o banco."""

    report_bytes = report_file.read_bytes()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    report = json.loads(report_bytes.decode("utf-8"))

    if manifest.get("schema_version") != "corporate-event-reconciliation-manifest.v1":
        raise ValueError("schema do manifesto desconhecido")
    actual_sha256 = hashlib.sha256(report_bytes).hexdigest()
    if manifest.get("report_sha256") != actual_sha256:
        raise ValueError("SHA-256 do relatorio nao confere com o manifesto")
    if manifest.get("report_schema_version") != report.get("schema_version"):
        raise ValueError("schema do relatorio nao confere com o manifesto")
    if report.get("dry_run") is not True:
        raise ValueError("artefato nao esta marcado como dry-run")
    if report.get("database_writes_executed") != 0:
        raise ValueError("artefato registra escritas no banco")
    if not str(manifest.get("dataset_id") or "").strip():
        raise ValueError("manifesto exige dataset_id")
    window_start = manifest.get("window_start")
    window_end = manifest.get("window_end")
    if (window_start is None) != (window_end is None):
        raise ValueError("manifesto possui janela incompleta")
    if window_start is not None:
        try:
            parsed_start = date.fromisoformat(window_start)
            parsed_end = date.fromisoformat(window_end)
        except (TypeError, ValueError):
            raise ValueError("janela do manifesto deve usar datas ISO") from None
        if parsed_start > parsed_end:
            raise ValueError("janela do manifesto esta invertida")
    source_sha = manifest.get("source_commit_sha")
    if source_sha is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", source_sha):
        raise ValueError("source_commit_sha invalido no manifesto")
    artifact_context = report.get("artifact_context")
    if not isinstance(artifact_context, dict):
        raise ValueError("relatorio exige artifact_context")
    for field in ("dataset_id", "window_start", "window_end", "source_commit_sha"):
        if artifact_context.get(field) != manifest.get(field):
            raise ValueError(f"contexto {field} do relatorio diverge do manifesto")

    return {
        "valid": True,
        "report_sha256": actual_sha256,
        "report_schema_version": report.get("schema_version"),
        "dry_run": True,
        "database_writes_executed": 0,
        "dataset_id": manifest["dataset_id"],
        "window_start": window_start,
        "window_end": window_end,
        "source_commit_sha": source_sha,
    }
