"""Regressões do bootstrap legado do catálogo de eventos corporativos."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260731_corporate_event_catalog.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "corporate_event_catalog_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Inspector:
    def __init__(self, *, table_exists: bool) -> None:
        self.table_exists = table_exists

    def has_table(self, table_name: str) -> bool:
        assert table_name == "corporate_events"
        return self.table_exists


class _OperationRecorder:
    def __init__(self) -> None:
        self.created_tables: list[tuple[str, tuple[Any, ...]]] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...]]] = []

    def get_bind(self) -> object:
        return object()

    def create_table(self, name: str, *elements: Any) -> None:
        self.created_tables.append((name, elements))

    def create_index(self, name: str, table: str, columns: list[str]) -> None:
        self.created_indexes.append((name, table, tuple(columns)))


def test_bootstrap_preserves_existing_legacy_table(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)
    monkeypatch.setattr(
        migration.sa,
        "inspect",
        lambda bind: _Inspector(table_exists=True),
    )

    migration._bootstrap_legacy_corporate_events_if_missing()

    assert recorder.created_tables == []
    assert recorder.created_indexes == []


def test_bootstrap_creates_legacy_compatible_base_when_missing(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)
    monkeypatch.setattr(
        migration.sa,
        "inspect",
        lambda bind: _Inspector(table_exists=False),
    )

    migration._bootstrap_legacy_corporate_events_if_missing()

    assert [name for name, _ in recorder.created_tables] == ["corporate_events"]
    assert recorder.created_indexes == [
        ("ix_corporate_events_id", "corporate_events", ("id",)),
        ("ix_corporate_events_asset_id", "corporate_events", ("asset_id",)),
        ("ix_corporate_events_ticker", "corporate_events", ("ticker",)),
    ]

    column_names = {
        element.name
        for element in recorder.created_tables[0][1]
        if hasattr(element, "name") and element.name is not None
    }
    assert {
        "id",
        "asset_id",
        "ticker",
        "event_type",
        "status",
        "event_date",
        "ratio",
        "description",
        "brapi_event_id",
        "raw_data",
        "applied_at",
        "portfolio_id",
    } <= column_names
