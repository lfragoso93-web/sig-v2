"""Regressoes para consumidores de modelos ORM removidos e import completo da API."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[1] / "app"
_REMOVED_MODEL_IMPORTS = {
    "app.models.irpf": {"IRPFReport"},
    "app.models.config": {"AppConfig"},
}


def _removed_model_imports(path: Path) -> list[str]:
    findings: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _REMOVED_MODEL_IMPORTS:
            forbidden_names = _REMOVED_MODEL_IMPORTS[node.module]
            for alias in node.names:
                if alias.name in forbidden_names or alias.name == "*":
                    findings.append(
                        f"{path.relative_to(_APP_DIR)}:{node.lineno}: "
                        f"from {node.module} import {alias.name}"
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _REMOVED_MODEL_IMPORTS:
                    findings.append(
                        f"{path.relative_to(_APP_DIR)}:{node.lineno}: "
                        f"import {alias.name}"
                    )

    return findings


def test_runtime_has_no_consumers_of_removed_models() -> None:
    findings: list[str] = []

    for path in sorted(_APP_DIR.rglob("*.py")):
        findings.extend(_removed_model_imports(path))

    assert findings == []


def test_main_module_imports_without_removed_model_dependencies() -> None:
    module = importlib.import_module("app.main")

    assert module.app is not None
