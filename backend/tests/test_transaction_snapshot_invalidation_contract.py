from __future__ import annotations

import ast
import inspect

from app.routers import transactions


def _function(name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(inspect.getsource(transactions))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"função {name} não encontrada")


def _called_names(function: ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def _call_order(function: ast.AsyncFunctionDef) -> list[str]:
    calls: list[tuple[int, int, str]] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue
        calls.append((node.lineno, node.col_offset, name))
    return [name for _, _, name in sorted(calls)]


def test_transaction_mutations_schedule_snapshot_and_cache_invalidation() -> None:
    for function_name in (
        "create_transaction",
        "update_transaction",
        "delete_transaction",
    ):
        called = _called_names(_function(function_name))
        assert "add_task" in called

        source = ast.unparse(_function(function_name))
        assert "_run_snapshot_backfill" in source
        assert "invalidate_portfolio_cache" in source


def test_snapshot_backfill_invalidates_before_rebuild() -> None:
    calls = _call_order(_function("_run_snapshot_backfill"))

    assert "invalidate_snapshots_from" in calls
    assert "backfill_snapshots" in calls
    assert calls.index("invalidate_snapshots_from") < calls.index("backfill_snapshots")
