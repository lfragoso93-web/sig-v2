"""Contract tests for persisted corporate-event reconciliation evidence."""

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
    / "20260917_corporate_event_reconciliation_evidence.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "corporate_event_reconciliation_evidence_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _OperationRecorder:
    def __init__(self) -> None:
        self.created_tables: list[tuple[str, tuple[Any, ...]]] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...], bool]] = []
        self.dropped_indexes: list[tuple[str, str | None]] = []
        self.dropped_tables: list[str] = []

    def create_table(self, name: str, *elements: Any) -> None:
        self.created_tables.append((name, elements))

    def create_index(
        self,
        name: str,
        table_name: str,
        columns: list[str],
        *,
        unique: bool = False,
    ) -> None:
        self.created_indexes.append(
            (name, table_name, tuple(columns), unique)
        )

    def drop_index(self, name: str, *, table_name: str | None = None) -> None:
        self.dropped_indexes.append((name, table_name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)


def test_upgrade_creates_reconciliation_evidence_contract(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert [name for name, _ in recorder.created_tables] == [
        "corporate_event_reconciliation_evidence",
    ]

    elements = recorder.created_tables[0][1]
    columns = {
        element.name: element
        for element in elements
        if isinstance(element, sa.Column)
    }

    assert set(columns) == {
        "id",
        "corporate_event_id",
        "decision",
        "evidence_type",
        "evidence_reference",
        "fractional_policy",
        "fractional_quantity",
        "fractional_settlement_price",
        "cash_treatment",
        "created_at",
    }

    assert columns["corporate_event_id"].nullable is False
    assert columns["decision"].nullable is False
    assert columns["evidence_type"].nullable is False
    assert columns["evidence_reference"].nullable is False
    assert columns["fractional_policy"].nullable is False
    assert columns["fractional_quantity"].nullable is True
    assert columns["fractional_settlement_price"].nullable is True
    assert columns["cash_treatment"].nullable is True
    assert columns["created_at"].nullable is False

    foreign_keys = [
        element
        for element in elements
        if element.__class__.__name__ == "ForeignKeyConstraint"
    ]
    assert len(foreign_keys) == 1
    assert list(foreign_keys[0].column_keys) == ["corporate_event_id"]
    assert [element.target_fullname for element in foreign_keys[0].elements] == [
        "corporate_events.id",
    ]

    unique_constraints = [
        element
        for element in elements
        if element.__class__.__name__ == "UniqueConstraint"
    ]
    assert len(unique_constraints) == 1
    assert unique_constraints[0].name == (
        "uq_corporate_event_reconciliation_evidence_event"
    )

    assert recorder.created_indexes == [
        (
            "ix_corporate_event_reconciliation_evidence_corporate_event_id",
            "corporate_event_reconciliation_evidence",
            ("corporate_event_id",),
            False,
        ),
    ]


def test_downgrade_removes_only_reconciliation_evidence_contract(
    monkeypatch: Any,
) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_indexes == [
        (
            "ix_corporate_event_reconciliation_evidence_corporate_event_id",
            "corporate_event_reconciliation_evidence",
        ),
    ]
    assert recorder.dropped_tables == [
        "corporate_event_reconciliation_evidence",
    ]


def test_migration_extends_current_single_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20260917_corp_event_recon_ev"
    assert migration.down_revision == "20260911_rate_annual_comment"
