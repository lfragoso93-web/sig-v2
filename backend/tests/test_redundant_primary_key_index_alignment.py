"""Gates para impedir indices ORM redundantes sobre chaves primarias."""

from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MODELS = {
    "asset_dividend.py": "AssetDividend",
    "audit_log.py": "AuditLog",
    "portfolio_snapshot.py": "PortfolioSnapshot",
}


def _id_call_for(path: Path, class_name: str) -> ast.Call:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if not isinstance(stmt, ast.AnnAssign):
                    continue
                if not isinstance(stmt.target, ast.Name) or stmt.target.id != "id":
                    continue
                if isinstance(stmt.value, ast.Call):
                    return stmt.value
    raise AssertionError(f"id mapped column not found in {path.name}:{class_name}")


def test_selected_primary_keys_do_not_request_redundant_indexes() -> None:
    for filename, class_name in _MODELS.items():
        call = _id_call_for(_BACKEND_ROOT / "app" / "models" / filename, class_name)
        keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg is not None}

        assert "primary_key" in keywords
        assert isinstance(keywords["primary_key"], ast.Constant)
        assert keywords["primary_key"].value is True
        assert "index" not in keywords


def test_gate_covers_current_alembic_pk_index_false_positives() -> None:
    assert set(_MODELS) == {
        "asset_dividend.py",
        "audit_log.py",
        "portfolio_snapshot.py",
    }
