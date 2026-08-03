"""Regression guards for the public dividend enums."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
ENUMS_PATH = APP_ROOT / "models" / "dividend_enums.py"


def test_dividend_enums_have_no_orm_or_legacy_model_dependency() -> None:
    tree = ast.parse(ENUMS_PATH.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert not any(module.startswith("sqlalchemy") for module in imported_modules)
    assert "app.models.dividend" not in imported_modules


def test_application_does_not_import_legacy_orm_module() -> None:
    offenders: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "app.models.dividend"
            ):
                offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []
