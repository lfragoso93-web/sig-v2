"""Regression guard for removal of portfolio dividend reconciliation."""

from __future__ import annotations

import ast
from pathlib import Path

SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "dividend_entitlement_service.py"
)


def test_entitlement_service_keeps_only_pure_shared_calculations() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert function_names == {"calculate_net_quantity", "calculate_net_value"}
    assert "reconcile_portfolio_dividend_rights" not in source
    assert "sqlalchemy" not in imported_modules
    assert "sqlalchemy.ext.asyncio" not in imported_modules
    assert {"Asset", "AssetDividend", "Dividend", "Transaction"}.isdisjoint(
        imported_names
    )
