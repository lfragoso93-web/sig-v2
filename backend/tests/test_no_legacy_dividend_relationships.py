"""Regression guards for removal of materialized-right ORM relationships."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_ROOT = BACKEND_ROOT / "app" / "models"


def _class_attributes(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    target = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    attributes: set[str] = set()
    for node in target.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            attributes.add(node.target.id)
        elif isinstance(node, ast.Assign):
            attributes.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
    return attributes


def test_parent_models_do_not_expose_materialized_dividend_collections() -> None:
    assert "dividends" not in _class_attributes(
        MODELS_ROOT / "portfolio.py", "Portfolio"
    )
    assert "portfolio_dividends" not in _class_attributes(
        MODELS_ROOT / "asset_dividend.py", "AssetDividend"
    )


def test_legacy_dividend_model_has_no_navigation_relationships() -> None:
    attributes = _class_attributes(MODELS_ROOT / "dividend.py", "Dividend")

    assert {"portfolio", "asset_dividend"}.isdisjoint(attributes)
    source = (MODELS_ROOT / "dividend.py").read_text(encoding="utf-8")
    assert "relationship(" not in source
    assert "back_populates" not in source
