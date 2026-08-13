from __future__ import annotations

import ast
import inspect
from pathlib import Path

from app.services import persisted_fx_query_service, portfolio_summary_service


SNAPSHOT_SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "portfolio_snapshot_service.py"
)
SNAPSHOT_PRICE_RESOLUTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "snapshot_price_resolution_service.py"
)


def _imported_modules(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_summary_uses_persisted_fx_query_only() -> None:
    source = inspect.getsource(portfolio_summary_service)

    assert "get_persisted_usd_brl_rate" in source
    assert "get_usd_brl_today" not in source
    assert "app.services.fx_service" not in source


def test_persisted_fx_query_has_no_provider_imports() -> None:
    imported = _imported_modules(persisted_fx_query_service)

    assert not any("bcb" in module.lower() for module in imported)
    assert not any("brapi" in module.lower() for module in imported)
    assert not any("httpx" in module.lower() for module in imported)
    assert not any("awesome" in module.lower() for module in imported)


def test_snapshot_price_resolution_has_no_provider_boundary() -> None:
    source = SNAPSHOT_PRICE_RESOLUTION_PATH.read_text(encoding="utf-8")

    forbidden = (
        "price_date_gap_resolver_service",
        "resolve_price_at_date_gap",
        "app.integrations",
        "yfinance",
        "httpx",
        "brapi",
    )
    assert not any(token in source for token in forbidden)


def test_snapshot_service_must_not_use_provider_fx() -> None:
    source = SNAPSHOT_SERVICE_PATH.read_text(encoding="utf-8")

    assert "app.services.fx_service" not in source
    assert "get_usd_brl_today" not in source
    assert "get_usd_brl_for_date" not in source
    assert "get_persisted_usd_brl_rate_for_date" in source
