"""Regress?o estrutural das muta??es de transa??es sem materializa??o."""

from __future__ import annotations

import ast
from pathlib import Path


ROUTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "transactions.py"
)


def test_transaction_mutations_do_not_materialize_dividend_rights() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    imported_names: set[str] = set()
    function_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module)
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_names.add(node.name)

    assert "app.services.dividend_entitlement_service" not in imported_modules
    assert "reconcile_portfolio_dividend_rights" not in imported_names
    assert "_run_dividend_reconciliation" not in function_names
    assert "reconcile_portfolio_dividend_rights" not in source
    assert "_run_dividend_reconciliation" not in source


def test_transaction_mutations_preserve_global_collection_and_invalidations() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")

    assert "backfill_dividends" in source
    assert "run_onboarding" in source
    assert "_run_snapshot_backfill" in source
    assert "invalidate_portfolio_cache" in source
