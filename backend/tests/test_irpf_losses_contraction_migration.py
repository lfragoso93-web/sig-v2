"""Gates para a contração isolada de ``irpf_losses``."""

from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = (
    _BACKEND_ROOT
    / "alembic"
    / "versions"
    / "20260806_drop_irpf_losses.py"
)


def _drop_table_arguments(source: str) -> list[str]:
    tree = ast.parse(source, filename=str(_MIGRATION))
    arguments: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "drop_table":
            continue
        if node.args and isinstance(node.args[0], ast.Name):
            arguments.append(node.args[0].id)
        elif node.args and isinstance(node.args[0], ast.Constant):
            arguments.append(str(node.args[0].value))
    return arguments


def test_irpf_losses_migration_is_isolated_and_guarded() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260806_drop_irpf_losses"' in source
    assert 'down_revision: str = "20260806_drop_goal_allocations"' in source
    assert '_TABLE = "irpf_losses"' in source
    assert "SELECT COUNT(*)" in source
    assert "physical contraction blocked" in source
    assert _drop_table_arguments(source) == ["_TABLE"]


def test_irpf_losses_downgrade_restores_original_contract() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'name="irpfmarket"' in source
    assert "create_type=False" in source
    assert 'sa.ForeignKey("users.id", ondelete="CASCADE")' in source
    assert '"accumulated_loss"' in source
    assert 'op.create_index("ix_irpf_losses_id"' in source


def test_irpf_losses_migration_preserves_shared_enum() -> None:
    source = _MIGRATION.read_text(encoding="utf-8").lower()

    assert "drop type" not in source
    assert "irpfmarket" in source
