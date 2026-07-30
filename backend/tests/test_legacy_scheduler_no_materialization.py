import ast
from pathlib import Path


SCHEDULER_PATH = Path(__file__).parents[1] / "app" / "scheduler.py"


def test_legacy_scheduler_does_not_import_or_call_materialization() -> None:
    tree = ast.parse(SCHEDULER_PATH.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "app.services.dividend_backfill_service" not in imported_modules
    assert "backfill_dividends" not in imported_names
    assert "materialize_asset_dividends" not in imported_names
    assert "backfill_dividends" not in called_names
    assert "materialize_asset_dividends" not in called_names


def test_legacy_scheduler_does_not_write_materialized_dividends() -> None:
    tree = ast.parse(SCHEDULER_PATH.read_text(encoding="utf-8"))

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    job_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "app.models.dividend" not in imported_modules
    assert "Dividend" not in imported_names
    assert "job_sync_dividends" not in job_names
    assert "job_update_dividend_status" not in job_names
