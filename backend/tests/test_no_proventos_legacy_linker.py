"""Regression guard for removal of the obsolete legacy-right linker."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
LEGACY_PATHS = (
    APP_ROOT / "services" / "proventos_legacy_link_service.py",
    APP_ROOT / "cli" / "dry_run_proventos_legacy_links.py",
)
LEGACY_MODULES = {
    "app.services.proventos_legacy_link_service",
    "app.cli.dry_run_proventos_legacy_links",
}


def test_legacy_linker_service_and_cli_are_removed() -> None:
    assert [str(path) for path in LEGACY_PATHS if path.exists()] == []


def test_application_does_not_import_legacy_linker_modules() -> None:
    offenders: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported_modules = (
                {node.module}
                if isinstance(node, ast.ImportFrom) and node.module
                else {alias.name for alias in node.names}
                if isinstance(node, ast.Import)
                else set()
            )
            if imported_modules & LEGACY_MODULES:
                offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []
