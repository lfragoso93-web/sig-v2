from __future__ import annotations

import ast
import inspect

from app.services import persisted_fx_query_service, portfolio_summary_service


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
