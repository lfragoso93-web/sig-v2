from __future__ import annotations

import ast
from pathlib import Path


ROUTER_PATH = Path(__file__).parents[1] / "app" / "routers" / "performance.py"


def test_performance_router_is_valid_python_source() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")

    ast.parse(source)
    assert r"\n" not in source
