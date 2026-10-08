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
    / "20261008_treasury_instruments.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "treasury_instruments_migration",
        MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _OperationRecorder:
    def __init__(self) -> None:
        self.created_tables: list[tuple[str, tuple[Any, ...]]] = []
        self.dropped_tables: list[str] = []

    def create_table(self, name: str, *elements: Any) -> None:
        self.created_tables.append((name, elements))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)


def test_upgrade_creates_nullable_one_to_one_metadata_contract(
    monkeypatch: Any,
) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert [name for name, _ in recorder.created_tables] == [
        "treasury_instruments"
    ]
    elements = recorder.created_tables[0][1]
    columns = {
        element.name: element
        for element in elements
        if isinstance(element, sa.Column)
    }
    assert set(columns) == {
        "asset_id",
        "commercial_name",
        "bond_type",
        "indexer",
        "coupon_type",
        "maturity_date",
        "official_code",
        "issuer",
        "trading_status",
        "metadata_source",
        "source_reference",
        "source_observed_at",
        "created_at",
        "updated_at",
    }
    assert columns["asset_id"].nullable is False
    assert columns["created_at"].nullable is False
    assert columns["updated_at"].nullable is False
    optional = set(columns) - {"asset_id", "created_at", "updated_at"}
    assert all(columns[name].nullable is True for name in optional)

    primary_keys = [
        element
        for element in elements
        if isinstance(element, sa.PrimaryKeyConstraint)
    ]
    assert len(primary_keys) == 1
    assert primary_keys[0].name == "pk_treasury_instruments"
    assert list(primary_keys[0]._pending_colargs) == ["asset_id"]

    foreign_keys = [
        element
        for element in elements
        if isinstance(element, sa.ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    assert foreign_keys[0].name == "fk_treasury_instruments_asset"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_migration_extends_head_without_changing_runtime_target() -> None:
    migration = _load_migration()
    entrypoint = (
        Path(__file__).resolve().parents[1] / "entrypoint.sh"
    ).read_text(encoding="utf-8")

    assert migration.revision == "20261008_treasury_instruments"
    assert migration.down_revision == "20261005_real_data_cert"
    assert 'RUNTIME_MIGRATION_TARGET="20261005_real_data_cert"' in entrypoint


def test_downgrade_removes_only_treasury_metadata_table(
    monkeypatch: Any,
) -> None:
    migration = _load_migration()
    recorder = _OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_tables == ["treasury_instruments"]
