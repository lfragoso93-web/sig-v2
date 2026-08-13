"""Gates arquiteturais para manter o CRUD de transacoes livre de sync externo."""

from __future__ import annotations

import ast
from pathlib import Path

_ROUTER_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "transactions.py"
_FORBIDDEN_IMPORTS = {
    "app.services.asset_onboarding_service",
    "app.services.dividend_backfill_service",
    "app.services.asset_market_pipeline_service",
}
_FORBIDDEN_CALL_NAMES = {
    "run_onboarding",
    "backfill_dividends",
    "sync_asset_market_data",
}


def test_transactions_router_does_not_import_external_market_sync_services() -> None:
    tree = ast.parse(_ROUTER_PATH.read_text(encoding="utf-8"), filename=str(_ROUTER_PATH))
    findings: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _FORBIDDEN_IMPORTS:
            findings.append(f"{node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _FORBIDDEN_IMPORTS:
                    findings.append(f"{node.lineno}: import {alias.name}")

    assert findings == []


def test_transactions_router_does_not_schedule_external_market_sync() -> None:
    tree = ast.parse(_ROUTER_PATH.read_text(encoding="utf-8"), filename=str(_ROUTER_PATH))
    findings: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name in _FORBIDDEN_CALL_NAMES:
            findings.append(f"{node.lineno}: {name}()")

    assert findings == []


def test_transactions_router_keeps_local_snapshot_recalculation() -> None:
    source = _ROUTER_PATH.read_text(encoding="utf-8")

    assert "_run_snapshot_backfill" in source
    assert "invalidate_portfolio_cache" in source
    assert "get_or_create_asset" in source
