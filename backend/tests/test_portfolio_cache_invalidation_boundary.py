"""Contrato fail-open sem silenciamento redundante na invalidação de carteira."""

from __future__ import annotations

import ast
from pathlib import Path


SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"
TARGETS = (
    (SERVICES / "portfolio_service.py", "invalidate_portfolio_cache"),
    (SERVICES / "portfolio_delete_service.py", "_invalidate_portfolio_cache"),
)


def _function(path: Path, function_name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )


def test_portfolio_cache_invalidators_delegate_without_silent_catches() -> None:
    for path, function_name in TARGETS:
        function = _function(path, function_name)
        calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "cache_delete"
        ]

        assert len(calls) == 2
        assert not any(isinstance(node, ast.ExceptHandler) for node in ast.walk(function))
