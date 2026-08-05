from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
LEGACY_MODULE = "app.services.rentabilidade_service"
ALLOWED_SOURCE = APP_ROOT / "services" / "rentabilidade_service.py"
EXPECTED_LEGACY_CONSUMERS = {
    "app/routers/portfolios.py",
    "app/routers/transactions.py",
    "app/services/csv_snapshot_rebuild_service.py",
}


def _iter_python_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _imports_legacy_module(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == LEGACY_MODULE for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == LEGACY_MODULE:
                return True
    return False


def test_legacy_rentabilidade_imports_match_migration_baseline() -> None:
    consumers = {
        path.relative_to(BACKEND_ROOT).as_posix()
        for path in _iter_python_files()
        if path != ALLOWED_SOURCE and _imports_legacy_module(path)
    }

    assert consumers == EXPECTED_LEGACY_CONSUMERS, (
        "Os imports do serviço legado de rentabilidade devem corresponder ao "
        "baseline temporário da Issue #151. Atualize o consumidor e este baseline "
        "no mesmo bloco. "
        f"Esperados: {sorted(EXPECTED_LEGACY_CONSUMERS)}; "
        f"encontrados: {sorted(consumers)}"
    )
