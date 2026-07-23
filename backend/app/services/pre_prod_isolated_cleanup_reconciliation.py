"""Read-only row-count evidence for isolated cleanup rehearsals."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IsolatedCleanupReconciliationError(RuntimeError):
    pass


def load_classifications(
    *, plan_path: Path, plan_payload: Mapping[str, Any]
) -> dict[str, str]:
    artifacts = plan_payload.get("artifacts")
    relative: str | None = None
    if isinstance(artifacts, list):
        for item in artifacts:
            if isinstance(item, Mapping) and item.get("kind") == "cleanup_impact":
                value = item.get("relative_path")
                if isinstance(value, str):
                    relative = value
                    break
    if relative is None or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise IsolatedCleanupReconciliationError("safe cleanup impact path is required")
    try:
        impact = json.loads((plan_path.parent.parent / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IsolatedCleanupReconciliationError("invalid cleanup impact artifact") from exc
    tables = impact.get("tables") if isinstance(impact, Mapping) else None
    if not isinstance(tables, list):
        raise IsolatedCleanupReconciliationError("invalid cleanup impact tables")
    result: dict[str, str] = {}
    for item in tables:
        if not isinstance(item, Mapping):
            raise IsolatedCleanupReconciliationError("invalid cleanup impact table")
        name, classification = item.get("name"), item.get("classification")
        if (
            not isinstance(name, str)
            or not _SAFE_IDENTIFIER.fullmatch(name)
            or not isinstance(classification, str)
            or name in result
        ):
            raise IsolatedCleanupReconciliationError("invalid cleanup impact classification")
        result[name] = classification
    return result


def capture_counts(
    connection: Connection, classifications: Mapping[str, str]
) -> dict[str, Any]:
    tables = []
    for name in sorted(classifications):
        count = connection.execute(text(f'SELECT count(*) FROM "{name}"')).scalar_one()
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise IsolatedCleanupReconciliationError("invalid database row count")
        tables.append({"name": name, "classification": classifications[name], "row_count": count})
    return {
        "schema_version": "pre-prod-cleanup-counts.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "tables": tables,
    }


def preserved(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pre-prod-preserved-tables.v1",
        "generated_at": snapshot["generated_at"],
        "read_only": True,
        "tables": [
            item for item in snapshot["tables"]
            if item["classification"] == "preserved"
        ],
    }


def reconcile(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    cleanup_order: tuple[str, ...],
    *,
    committed: bool,
) -> dict[str, Any]:
    baseline = {item["name"]: item["row_count"] for item in before["tables"]}
    final = {item["name"]: item["row_count"] for item in after["tables"]}
    cleanup = set(cleanup_order)
    table_set_unchanged = baseline.keys() == final.keys()
    non_cleanup_unchanged = all(
        baseline[name] == final.get(name) for name in baseline if name not in cleanup
    )
    cleanup_valid = all(
        final.get(name) == (0 if committed else baseline.get(name)) for name in cleanup
    )
    return {
        "schema_version": "pre-prod-isolated-cleanup-reconciliation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected_state": "committed" if committed else "rolled_back",
        "ok": table_set_unchanged and non_cleanup_unchanged and cleanup_valid,
        "table_set_unchanged": table_set_unchanged,
        "preserved_tables_unchanged": non_cleanup_unchanged,
        "cleanup_tables_match_expected_state": cleanup_valid,
        "cleanup_order": list(cleanup_order),
    }


def publish(destination: Path, payload: Mapping[str, Any]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise IsolatedCleanupReconciliationError(
                f"evidence already exists: {destination}"
            ) from exc
        return destination
    finally:
        temporary.unlink(missing_ok=True)
