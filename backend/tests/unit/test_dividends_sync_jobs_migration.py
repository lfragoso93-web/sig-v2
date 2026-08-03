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
    / "20260728_create_dividends_sync_jobs.py"
)


def _load_migration():
    alembic_module = ModuleType("alembic")
    alembic_module.op = Mock()
    spec = importlib.util.spec_from_file_location(
        "create_dividends_sync_jobs",
        MIGRATION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"alembic": alembic_module}):
        spec.loader.exec_module(module)
    return module


def test_upgrade_materializes_the_complete_orm_table() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "create_table") as create_table,
        patch.object(migration.op, "create_index") as create_index,
    ):
        migration.upgrade()

    table_name, *elements = create_table.call_args.args
    migration_columns = {
        element.name for element in elements if hasattr(element, "type")
    }

    assert table_name == "dividends_sync_jobs"
    assert migration_columns == {
        "id",
        "job_name",
        "status",
        "started_at",
        "finished_at",
        "last_success_at",
        "last_cursor_date",
        "last_run_assets_processed",
        "last_run_events_created",
        "last_run_events_updated",
        "last_run_errors",
        "locked_by",
        "locked_at",
        "error_message",
        "created_at",
        "updated_at",
    }
    create_index.assert_called_once_with(
        "ix_dividends_sync_jobs_job_name",
        "dividends_sync_jobs",
        ["job_name"],
        unique=True,
    )


def test_revision_extends_the_current_merged_head() -> None:
    migration = _load_migration()

    assert migration.revision == "20260728_dividends_sync_jobs"
    assert migration.down_revision == "20260724_merge_heads"


def test_downgrade_removes_index_before_table() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "drop_index") as drop_index,
        patch.object(migration.op, "drop_table") as drop_table,
    ):
        migration.downgrade()

    drop_index.assert_called_once_with(
        "ix_dividends_sync_jobs_job_name",
        table_name="dividends_sync_jobs",
    )
    drop_table.assert_called_once_with("dividends_sync_jobs")
