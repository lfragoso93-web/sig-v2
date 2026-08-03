"""Regression guard for the active portfolio deletion boundary."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_SERVICE = BACKEND_ROOT / "app" / "services" / "portfolio_service.py"
PORTFOLIOS_ROUTER = BACKEND_ROOT / "app" / "routers" / "portfolios.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_portfolio_service_has_no_orphan_delete_or_dividend_dependency() -> None:
    tree = _tree(PORTFOLIO_SERVICE)
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

    assert "delete_portfolio" not in function_names
    assert "app.models.dividend" not in imported_modules
    assert "Dividend" not in imported_names


def test_portfolio_router_uses_safe_delete_service() -> None:
    tree = _tree(PORTFOLIOS_ROUTER)
    imported_safe_delete = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app.services.portfolio_delete_service"
        and any(alias.name == "delete_portfolio_safely" for alias in node.names)
        for node in ast.walk(tree)
    )
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert imported_safe_delete
    assert "delete_portfolio_safely" in called_names
    assert "delete_portfolio" not in called_names
