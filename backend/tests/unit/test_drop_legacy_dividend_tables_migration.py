from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, call, patch

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260731_drop_legacy_dividend_tables.py"
)


def _load_migration():
    alembic_module = ModuleType("alembic")
    alembic_module.op = Mock()
    spec = importlib.util.spec_from_file_location(
        "drop_legacy_dividend_tables",
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

    assert migration.revision == "20260731_drop_legacy_divs"
    assert len(migration.revision) <= 32
    assert migration.down_revision == "20260729_dividend_identity"


def test_upgrade_checks_both_tables_before_dropping_in_dependency_order() -> None:
    migration = _load_migration()
    bind = Mock()
    bind.execute.side_effect = [_count_result(0), _count_result(0)]

    with (
        patch.object(migration.op, "get_bind", return_value=bind),
        patch.object(migration.op, "drop_table") as drop_table,
    ):
        migration.upgrade()

    assert [str(item.args[0]) for item in bind.execute.call_args_list] == [
        'SELECT COUNT(*) FROM "dividends"',
        'SELECT COUNT(*) FROM "dividends_sync_jobs"',
    ]
    assert drop_table.call_args_list == [
        call("dividends"),
        call("dividends_sync_jobs"),
    ]


@pytest.mark.parametrize(
    ("counts", "blocked_table"),
    [
        ((1,), "dividends"),
        ((0, 2), "dividends_sync_jobs"),
    ],
)
def test_upgrade_blocks_nonempty_legacy_tables_before_any_drop(
    counts: tuple[int, ...],
    blocked_table: str,
) -> None:
    migration = _load_migration()
    bind = Mock()
    bind.execute.side_effect = [_count_result(value) for value in counts]

    with (
        patch.object(migration.op, "get_bind", return_value=bind),
        patch.object(migration.op, "drop_table") as drop_table,
        pytest.raises(RuntimeError, match=blocked_table),
    ):
        migration.upgrade()

    drop_table.assert_not_called()


def test_downgrade_requires_backup_restore() -> None:
    migration = _load_migration()

    with pytest.raises(RuntimeError, match="restore"):
        migration.downgrade()
