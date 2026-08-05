from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
LEGACY_MODULE = "app.services.rentabilidade_service"
LEGACY_SOURCE = APP_ROOT / "services" / "rentabilidade_service.py"


def _iter_python_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _imports_legacy_module(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == LEGACY_MODULE for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module == LEGACY_MODULE:
            return True
    return False


def test_legacy_rentabilidade_service_is_removed() -> None:
    consumers = {
        path.relative_to(BACKEND_ROOT).as_posix()
        for path in _iter_python_files()
        if _imports_legacy_module(path)
    }

    assert not LEGACY_SOURCE.exists(), (
        "O serviço legado de rentabilidade deve permanecer removido conforme a Issue #151."
    )
    assert not consumers, (
        "Nenhum módulo de produção pode importar o serviço legado de rentabilidade. "
        f"Consumidores encontrados: {sorted(consumers)}"
    )
