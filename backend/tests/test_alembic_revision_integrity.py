"""Valida integridade basica da cadeia de revisions do Alembic."""
from __future__ import annotations

import ast
from pathlib import Path


VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _literal_assignment(path: Path, variable: str) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == variable for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None


def test_alembic_revision_ids_are_unique() -> None:
    revisions: dict[str, Path] = {}
    duplicates: list[str] = []

    for path in sorted(VERSIONS_DIR.glob("*.py")):
        revision = _literal_assignment(path, "revision")
        if revision is None:
            continue
        if revision in revisions:
            duplicates.append(f"{revision}: {revisions[revision].name}, {path.name}")
        else:
            revisions[revision] = path

    assert not duplicates, "Revisions Alembic duplicadas: " + "; ".join(duplicates)
