"""Contract tests for ledger-basis evidence migration."""

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
    / "20260922_corporate_event_evidence_ledger_basis.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "corporate_event_evidence_ledger_basis_migration",
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


def test_upgrade_adds_nullable_ledger_basis_contract(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert [table for table, _ in recorder.added_columns] == [
        "corporate_event_reconciliation_evidence",
        "corporate_event_reconciliation_evidence",
        "corporate_event_reconciliation_evidence",
    ]
    columns = {column.name: column for _, column in recorder.added_columns}
    assert set(columns) == {
        "ledger_basis",
        "ledger_transformation_reference",
        "ledger_quantity_factor",
    }
    assert columns["ledger_basis"].nullable is True
    assert isinstance(columns["ledger_basis"].type, sa.String)
    assert columns["ledger_basis"].type.length == 40
    assert columns["ledger_transformation_reference"].nullable is True
    assert isinstance(columns["ledger_transformation_reference"].type, sa.Text)
    assert columns["ledger_quantity_factor"].nullable is True
    assert isinstance(columns["ledger_quantity_factor"].type, sa.Numeric)
    assert columns["ledger_quantity_factor"].type.precision == 24
    assert columns["ledger_quantity_factor"].type.scale == 12


def test_downgrade_removes_only_ledger_basis_contract(monkeypatch: Any) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_columns == [
        ("corporate_event_reconciliation_evidence", "ledger_quantity_factor"),
        (
            "corporate_event_reconciliation_evidence",
            "ledger_transformation_reference",
        ),
        ("corporate_event_reconciliation_evidence", "ledger_basis"),
    ]


def test_migration_extends_current_single_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20260922_corp_ev_ledger_basis"
    assert migration.down_revision == "20260917_corp_event_recon_ev"
