"""Contract tests for the effective-date evidence migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import sqlalchemy as sa

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20261016_corp_event_evidence_effective_date.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "corporate_event_evidence_effective_date_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _OperationRecorder:
    def __init__(self) -> None:
        self.added_columns: list[tuple[str, sa.Column[Any]]] = []
        self.dropped_columns: list[tuple[str, str]] = []

    def add_column(self, table_name: str, column: sa.Column[Any]) -> None:
        self.added_columns.append((table_name, column))

    def drop_column(self, table_name: str, column_name: str) -> None:
        self.dropped_columns.append((table_name, column_name))


def test_upgrade_adds_nullable_effective_date_evidence(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert len(recorder.added_columns) == 1
    table_name, column = recorder.added_columns[0]
    assert table_name == "corporate_event_reconciliation_evidence"
    assert column.name == "effective_date"
    assert column.nullable is True
    assert isinstance(column.type, sa.Date)


def test_downgrade_removes_only_effective_date_evidence(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_columns == [
        ("corporate_event_reconciliation_evidence", "effective_date")
    ]


def test_migration_extends_current_runtime_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20261016_corp_ev_effective_date"
    assert migration.down_revision == "20261016_corp_eff_null"
