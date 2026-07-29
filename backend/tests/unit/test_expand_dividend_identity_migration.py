import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260729_expand_dividend_identity.py"
)


def _load_migration():
    alembic_module = ModuleType("alembic")
    alembic_module.op = Mock()
    spec = importlib.util.spec_from_file_location(
        "expand_dividend_identity_migration",
        MIGRATION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"alembic": alembic_module}):
        spec.loader.exec_module(migration)
    return migration


def test_upgrade_replaces_collapsing_constraint_with_economic_identity() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "drop_constraint") as drop_constraint,
        patch.object(migration.op, "execute") as execute,
    ):
        migration.upgrade()

    drop_constraint.assert_called_once_with(
        "uq_asset_dividend_asset_exdate_type",
        "asset_dividends",
        type_="unique",
    )
    sql = execute.call_args.args[0]
    assert "uq_asset_dividend_economic_identity" in sql
    assert "COALESCE(payment_date, ex_date)" in sql
    assert migration.revision == "20260729_expand_dividend_identity"
    assert migration.down_revision == "20260728_dividends_sync_jobs"


def test_downgrade_restores_previous_constraint() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "drop_index") as drop_index,
        patch.object(migration.op, "create_unique_constraint") as create_constraint,
    ):
        migration.downgrade()

    drop_index.assert_called_once_with(
        "uq_asset_dividend_economic_identity",
        table_name="asset_dividends",
    )
    create_constraint.assert_called_once_with(
        "uq_asset_dividend_asset_exdate_type",
        "asset_dividends",
        ["asset_id", "ex_date", "dividend_type"],
    )
