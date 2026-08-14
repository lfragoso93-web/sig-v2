"""Regression guard for removal of the orphan legacy position service."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
LEGACY_MODULE = "app.services.position_service"
LEGACY_SERVICE = APP_ROOT / "services" / "position_service.py"


def _imports_legacy_module(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == LEGACY_MODULE for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module == LEGACY_MODULE:
            return True
    return False


def test_legacy_position_service_is_removed() -> None:
    assert not LEGACY_SERVICE.exists(), (
        "O serviço órfão de posições consultava provider e duplicava o contrato "
        "canônico de portfolio_service/canonical_positions_service."
    )


def test_application_does_not_import_legacy_position_service() -> None:
    consumers = {
        path.relative_to(BACKEND_ROOT).as_posix()
        for path in sorted(APP_ROOT.rglob("*.py"))
        if _imports_legacy_module(path)
    }

    assert not consumers, (
        "Nenhum módulo de produção pode reintroduzir o serviço legado de posições. "
        f"Consumidores encontrados: {sorted(consumers)}"
    )
