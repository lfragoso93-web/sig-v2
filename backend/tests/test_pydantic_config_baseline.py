"""Baseline estrutural para a migração Pydantic ConfigDict da Issue #186.

Este teste deve ser atualizado no mesmo commit que remover a última configuração
legada. Enquanto a migração não termina, ele impede que novas ``class Config``
sejam adicionadas silenciosamente ao backend.
"""

from __future__ import annotations

import ast
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
EXPECTED_LEGACY_CONFIGS = {
    "schemas/audit_log.py:AuditLogResponse.Config",
    "schemas/portfolio.py:ClassTargetRead.Config",
    "schemas/portfolio.py:ClassTargetWithCurrent.Config",
    "schemas/portfolio.py:PortfolioRead.Config",
}


def _legacy_config_classes() -> set[str]:
    found: set[str] = set()

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(APP_ROOT).as_posix()

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            for child in node.body:
                if isinstance(child, ast.ClassDef) and child.name == "Config":
                    found.add(f"{relative_path}:{node.name}.Config")

    return found


def test_legacy_pydantic_config_inventory_is_explicit() -> None:
    """Falha quando uma nova configuração baseada em classe é introduzida."""

    assert _legacy_config_classes() == EXPECTED_LEGACY_CONFIGS
