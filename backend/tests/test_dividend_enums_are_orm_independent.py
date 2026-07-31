"""Regression guards for the public dividend enums."""

from __future__ import annotations

import ast
from pathlib import Path

from app.models.dividend import DividendStatus as LegacyDividendStatus
from app.models.dividend import DividendType as LegacyDividendType
from app.models.dividend_enums import DividendStatus, DividendType

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


def test_legacy_module_reexports_the_same_enum_objects() -> None:
    assert LegacyDividendType is DividendType
    assert LegacyDividendStatus is DividendStatus


def test_application_does_not_import_enums_from_legacy_orm_module() -> None:
    offenders: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        if path == APP_ROOT / "models" / "dividend.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "app.models.dividend"
                and {alias.name for alias in node.names}
                & {"DividendStatus", "DividendType"}
            ):
                offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []
