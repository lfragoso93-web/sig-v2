"""Regression guard for removal of the orphan legacy entitlement helpers."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
LEGACY_SERVICE = APP_ROOT / "services" / "dividend_entitlement_service.py"


def test_legacy_dividend_entitlement_service_is_removed() -> None:
    assert not LEGACY_SERVICE.exists()


def test_application_does_not_import_legacy_dividend_entitlement_service() -> None:
    legacy_module = "app.services.dividend_entitlement_service"
    offenders: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imports_legacy = (
                isinstance(node, ast.ImportFrom) and node.module == legacy_module
            ) or (
                isinstance(node, ast.Import)
                and any(alias.name == legacy_module for alias in node.names)
            )
            if imports_legacy:
                offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []
