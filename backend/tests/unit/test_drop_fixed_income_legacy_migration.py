from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260903_drop_fixed_income_legacy.py"
)


def _load_migration():
    alembic_module = ModuleType("alembic")
    alembic_module.op = Mock()
    spec = importlib.util.spec_from_file_location(
        "drop_fixed_income_legacy",
        MIGRATION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"alembic": alembic_module}):
        spec.loader.exec_module(module)
    return module


def _count_result(value: int) -> Mock:
    result = Mock()
    result.scalar_one.return_value = value
    return result


def test_revision_extends_current_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20260903_drop_fixed_income"
    assert len(migration.revision) <= 32
    assert migration.down_revision == "20260820_dividend_occurrence"


def test_upgrade_requires_empty_table_and_drops_table_and_enums() -> None:
    migration = _load_migration()
    bind = Mock()
    bind.execute.return_value = _count_result(0)

    with (
        patch.object(migration.op, "get_bind", return_value=bind),
        patch.object(migration.op, "drop_table") as drop_table,
        patch.object(migration.op, "execute") as execute,
    ):
        migration.upgrade()

    assert str(bind.execute.call_args.args[0]) == (
        'SELECT COUNT(*) FROM "fixed_income_investments"'
    )
    drop_table.assert_called_once_with("fixed_income_investments")
    assert [str(item.args[0]) for item in execute.call_args_list] == [
        'DROP TYPE IF EXISTS "fixedincometype"',
        'DROP TYPE IF EXISTS "indexertype"',
    ]


def test_upgrade_blocks_nonempty_table_before_any_drop() -> None:
    migration = _load_migration()
    bind = Mock()
    bind.execute.return_value = _count_result(2)

    with (
        patch.object(migration.op, "get_bind", return_value=bind),
        patch.object(migration.op, "drop_table") as drop_table,
        patch.object(migration.op, "execute") as execute,
        pytest.raises(RuntimeError, match="contains 2 rows"),
    ):
        migration.upgrade()

    drop_table.assert_not_called()
    execute.assert_not_called()


def test_downgrade_requires_backup_restore() -> None:
    migration = _load_migration()

    with pytest.raises(RuntimeError, match="restore"):
        migration.downgrade()
