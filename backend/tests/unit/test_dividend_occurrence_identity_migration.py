from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260820_dividend_occurrence.py"
)


def _load_migration():
    alembic_module = ModuleType("alembic")
    alembic_module.op = Mock()
    spec = importlib.util.spec_from_file_location(
        "dividend_occurrence_identity",
        MIGRATION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"alembic": alembic_module}):
        spec.loader.exec_module(module)
    return module


def test_revision_extends_current_runtime_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20260820_dividend_occurrence"
    assert len(migration.revision) <= 32
    assert migration.down_revision == "20260813_rate_history_metadata"


def test_upgrade_adds_value_to_occurrence_identity() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "drop_index") as drop_index,
        patch.object(migration.op, "execute") as execute,
    ):
        migration.upgrade()

    drop_index.assert_called_once_with(
        "uq_asset_dividend_economic_identity",
        table_name="asset_dividends",
    )
    sql = execute.call_args.args[0]
    assert "COALESCE(payment_date, ex_date)" in sql
    assert "value_per_unit" in sql


def test_downgrade_restores_previous_identity() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "drop_index"),
        patch.object(migration.op, "execute") as execute,
    ):
        migration.downgrade()

    sql = execute.call_args.args[0]
    assert "COALESCE(payment_date, ex_date)" in sql
    assert "value_per_unit" not in sql
