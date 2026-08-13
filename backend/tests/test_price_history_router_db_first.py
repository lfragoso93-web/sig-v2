"""Regressoes arquiteturais para a leitura DB-first de historico de precos."""

from __future__ import annotations

import ast
from pathlib import Path

_ROUTER_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "prices.py"
_FORBIDDEN_IMPORT_PREFIXES = (
    "app.integrations",
    "app.services.price_history_backfill_service",
    "app.services.asset_price_global_backfill_service",
)


def test_price_history_router_does_not_import_provider_or_backfill_layers() -> None:
    tree = ast.parse(_ROUTER_PATH.read_text(encoding="utf-8"), filename=str(_ROUTER_PATH))
    findings: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(_FORBIDDEN_IMPORT_PREFIXES):
                findings.append(f"{node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(_FORBIDDEN_IMPORT_PREFIXES):
                    findings.append(f"{node.lineno}: import {alias.name}")

    assert findings == []


def test_price_history_router_uses_db_first_reader_only() -> None:
    source = _ROUTER_PATH.read_text(encoding="utf-8")

    assert "from app.services.price_history_service import get_price_history" in source
    assert "await get_price_history(" in source
    assert "provedores externos" in source
    assert "dispara backfill" in source
