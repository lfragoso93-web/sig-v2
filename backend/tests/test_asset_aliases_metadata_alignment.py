"""Gates de alinhamento entre ``asset_aliases`` no ORM e no Alembic."""

from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MODEL = _BACKEND_ROOT / "app" / "models" / "asset_alias.py"
_MIGRATION = _BACKEND_ROOT / "alembic" / "versions" / "20260712_asset_aliases.py"


def _column_keywords(source: str, attribute_name: str) -> dict[str, ast.expr]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == attribute_name for target in node.targets):
            continue
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "Column":
            return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg is not None}
    raise AssertionError(f"Column {attribute_name!r} not found")


def test_asset_alias_id_does_not_request_redundant_pk_index() -> None:
    source = _MODEL.read_text(encoding="utf-8")
    keywords = _column_keywords(source, "id")

    assert "primary_key" in keywords
    assert isinstance(keywords["primary_key"], ast.Constant)
    assert keywords["primary_key"].value is True
    assert "index" not in keywords


def test_asset_alias_migration_does_not_create_id_index() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'sa.Column("id", sa.Integer(), primary_key=True)' in source
    assert "ix_asset_aliases_id" not in source
    assert 'op.create_index("ix_asset_aliases_asset_id"' in source
    assert 'op.create_index("ix_asset_aliases_alias_ticker"' in source
