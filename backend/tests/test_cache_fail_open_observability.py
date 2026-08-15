"""Contrato estrutural da fronteira Redis opcional e observável."""

from __future__ import annotations

import ast
from pathlib import Path


CACHE_PATH = Path(__file__).resolve().parents[1] / "app" / "core" / "cache.py"


def test_cache_boundary_has_no_silent_exception_handlers() -> None:
    source = CACHE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CACHE_PATH))
    handlers = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]

    assert len(handlers) == 5
    assert not any(
        isinstance(statement, ast.Pass)
        for handler in handlers
        for statement in handler.body
    )
    assert source.count("logger.warning(") == 5


def test_cache_logs_sanitize_keys_patterns_and_errors_without_values() -> None:
    source = CACHE_PATH.read_text(encoding="utf-8")

    assert "from app.core.log_safety import sanitize_log_value" in source
    assert source.count("sanitize_log_value(exc)") == 5
    assert source.count("sanitize_log_value(key)") == 3
    assert source.count("sanitize_log_value(pattern)") == 1
    assert "sanitize_log_value(value)" not in source
