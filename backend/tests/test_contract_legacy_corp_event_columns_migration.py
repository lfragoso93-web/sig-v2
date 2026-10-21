"""Contract tests for corporate_events legacy columns contraction migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock

import sqlalchemy as sa

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20261021_contract_legacy_corp_event_columns.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "contract_legacy_corp_event_columns_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Inspector:
    def __init__(self, table_exists: bool = True) -> None:
        self._table_exists = table_exists

    def has_table(self, table_name: str) -> bool:
        return self._table_exists

    def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        return [
            {"name": "id"},
            {"name": "effective_date"},
            {"name": "quantity_factor"},
            {"name": "source_event_id"},
            {"name": "raw_metadata"},
            {"name": "brapi_event_id"},
            {"name": "raw_data"},
            {"name": "event_date"},
            {"name": "ratio"},
        ]

    def get_unique_constraints(self, table_name: str) -> list[dict[str, Any]]:
        return [{"name": "uq_corporate_events_brapi_event_id"}]


class _OperationRecorder:
    def __init__(self) -> None:
        self.dropped_columns: list[tuple[str, str]] = []
        self.dropped_constraints: list[tuple[str, str, str]] = []
        self.added_columns: list[tuple[str, sa.Column[Any]]] = []
        self.created_constraints: list[tuple[str, str, list[str]]] = []
        self.executed_statements: list[str] = []

    def get_bind(self) -> Mock:
        bind = Mock()
        result = Mock()
        result.scalar_one.return_value = 0
        bind.execute.return_value = result
        return bind

    def drop_constraint(self, name: str, table_name: str, type_: str) -> None:
        self.dropped_constraints.append((name, table_name, type_))

    def drop_column(self, table_name: str, column_name: str) -> None:
        self.dropped_columns.append((table_name, column_name))

    def add_column(self, table_name: str, column: sa.Column[Any]) -> None:
        self.added_columns.append((table_name, column))

    def create_unique_constraint(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_constraints.append((name, table_name, columns))

    def execute(self, statement: Any) -> None:
        self.executed_statements.append(str(statement))


def test_migration_chain_identity() -> None:
    migration = _load_migration()

    assert migration.revision == "20261021_contract_corp_events"
    assert len(migration.revision) <= 32
    assert migration.down_revision == "20261019_corp_event_legs"


def test_upgrade_drops_constraint_and_legacy_columns(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: _Inspector())

    migration.upgrade()

    assert recorder.dropped_constraints == [
        ("uq_corporate_events_brapi_event_id", "corporate_events", "unique")
    ]
    assert recorder.dropped_columns == [
        ("corporate_events", "brapi_event_id"),
        ("corporate_events", "raw_data"),
        ("corporate_events", "event_date"),
        ("corporate_events", "ratio"),
    ]


def test_downgrade_restores_columns_and_constraint(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    # Empty columns inspector to simulate table after upgrade
    class _EmptyInspector(_Inspector):
        def get_columns(self, table_name: str) -> list[dict[str, Any]]:
            return [{"name": "id"}]

        def get_unique_constraints(self, table_name: str) -> list[dict[str, Any]]:
            return []

    monkeypatch.setattr(migration.sa, "inspect", lambda bind: _EmptyInspector())

    migration.downgrade()

    added_names = [col.name for _, col in recorder.added_columns]
    assert added_names == ["ratio", "event_date", "raw_data", "brapi_event_id"]
    assert recorder.created_constraints == [
        ("uq_corporate_events_brapi_event_id", "corporate_events", ["brapi_event_id"])
    ]
    assert any("UPDATE corporate_events" in stmt for stmt in recorder.executed_statements)
