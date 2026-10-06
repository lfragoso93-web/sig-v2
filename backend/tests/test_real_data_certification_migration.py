"""Contract tests for the persistent real-data certification event log."""

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
    / "20261005_real_data_certification.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "real_data_certification_migration",
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
        self.created_indexes.append((name, table_name, tuple(columns), unique))

    def drop_index(self, name: str, *, table_name: str | None = None) -> None:
        self.dropped_indexes.append((name, table_name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)


def test_upgrade_creates_append_only_certification_contract(
    monkeypatch: Any,
) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert [name for name, _ in recorder.created_tables] == [
        "real_data_certification_events"
    ]
    elements = recorder.created_tables[0][1]
    columns = {
        element.name: element
        for element in elements
        if isinstance(element, sa.Column)
    }
    assert set(columns) == {
        "id",
        "event_key",
        "action",
        "schema_version",
        "environment",
        "branch",
        "commit_sha",
        "dataset_reference",
        "alembic_revision",
        "gate_issue_reference",
        "pull_request_reference",
        "evidence_sha256",
        "evidence_payload",
        "actor",
        "reason",
        "supersedes_event_id",
        "created_at",
    }
    required = set(columns) - {
        "gate_issue_reference",
        "pull_request_reference",
        "supersedes_event_id",
    }
    assert all(columns[name].nullable is False for name in required)
    assert columns["gate_issue_reference"].nullable is True
    assert columns["pull_request_reference"].nullable is True
    assert columns["supersedes_event_id"].nullable is True

    check_constraints = [
        element
        for element in elements
        if element.__class__.__name__ == "CheckConstraint"
    ]
    assert len(check_constraints) == 1
    assert check_constraints[0].name == "ck_real_data_cert_events_action"

    foreign_keys = [
        element
        for element in elements
        if element.__class__.__name__ == "ForeignKeyConstraint"
    ]
    assert len(foreign_keys) == 1
    assert list(foreign_keys[0].column_keys) == ["supersedes_event_id"]

    unique_constraints = [
        element
        for element in elements
        if element.__class__.__name__ == "UniqueConstraint"
    ]
    assert [constraint.name for constraint in unique_constraints] == [
        "uq_real_data_certification_events_event_key"
    ]
    assert recorder.created_indexes == [
        (
            "ix_real_data_cert_events_environment_created_at",
            "real_data_certification_events",
            ("environment", "created_at"),
            False,
        )
    ]


def test_downgrade_removes_only_certification_contract(
    monkeypatch: Any,
) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_indexes == [
        (
            "ix_real_data_cert_events_environment_created_at",
            "real_data_certification_events",
        )
    ]
    assert recorder.dropped_tables == ["real_data_certification_events"]


def test_migration_extends_current_single_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20261005_real_data_cert"
    assert migration.down_revision == "20260922_corp_ev_ledger_basis"
