"""Regression guards for removal of the legacy-specific runtime inventory."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
REMOVED_PATHS = (
    APP_ROOT / "services" / "proventos_model_audit_service.py",
    APP_ROOT / "cli" / "audit_proventos_model.py",
)
REMOVED_MODULES = {
    "app.services.proventos_model_audit_service",
    "app.cli.audit_proventos_model",
}


def test_legacy_specific_audit_service_and_cli_are_removed() -> None:
    assert [str(path) for path in REMOVED_PATHS if path.exists()] == []


def test_application_does_not_import_removed_audit_modules() -> None:
    offenders: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = (
                {node.module}
                if isinstance(node, ast.ImportFrom) and node.module
                else {alias.name for alias in node.names}
                if isinstance(node, ast.Import)
                else set()
            )
            if modules & REMOVED_MODULES:
                offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []


def test_runtime_layers_do_not_import_legacy_dividend_model() -> None:
    offenders: list[str] = []

    for directory in ("cli", "routers", "schemas", "services"):
        for path in (APP_ROOT / directory).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if any(
                isinstance(node, ast.ImportFrom)
                and node.module == "app.models.dividend"
                and any(alias.name == "Dividend" for alias in node.names)
                for node in ast.walk(tree)
            ):
                offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []
