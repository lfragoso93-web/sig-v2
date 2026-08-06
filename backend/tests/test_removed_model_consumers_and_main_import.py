"""Regressoes para consumidores de modelos ORM removidos e import completo da API."""

from __future__ import annotations

import importlib
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[1] / "app"
_FORBIDDEN_RUNTIME_REFERENCES = (
    "from app.models.irpf import IRPFReport",
    "import app.models.irpf",
    "from app.models.config import AppConfig",
    "import app.models.config",
)


def test_runtime_has_no_consumers_of_removed_models() -> None:
    findings: list[str] = []

    for path in sorted(_APP_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_RUNTIME_REFERENCES:
            if forbidden in source:
                findings.append(f"{path.relative_to(_APP_DIR)}: {forbidden}")

    assert findings == []


def test_main_module_imports_without_removed_model_dependencies() -> None:
    module = importlib.import_module("app.main")

    assert module.app is not None
