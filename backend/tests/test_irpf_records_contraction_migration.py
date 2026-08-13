"""Gates para a contração isolada de ``irpf_records``."""

from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = (
    _BACKEND_ROOT
    / "alembic"
    / "versions"
    / "20260806_drop_irpf_records.py"
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


def test_irpf_records_migration_is_isolated_and_guarded() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260806_drop_irpf_records"' in source
    assert 'down_revision: str = "20260806_drop_irpf_losses"' in source
    assert '_TABLE = "irpf_records"' in source
    assert "SELECT COUNT(*)" in source
    assert "physical contraction blocked" in source
    assert _drop_table_arguments(source) == ["_TABLE"]


def test_irpf_records_downgrade_restores_original_contract() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'name="irpfmarket"' in source
    assert "create_type=False" in source
    assert 'sa.ForeignKey("users.id", ondelete="CASCADE")' in source
    assert 'sa.Column("gross_profit"' in source
    assert 'sa.Column("loss_offset"' in source
    assert 'sa.Column("taxable_profit"' in source
    assert 'sa.Column("ir_rate"' in source
    assert 'sa.Column("ir_due"' in source
    assert 'sa.Column("ir_withheld"' in source
    assert 'sa.Column("ir_to_pay"' in source
    assert 'sa.Column("is_exempt"' in source
    assert 'sa.Column("darf_code"' in source
    assert 'op.create_index("ix_irpf_records_id"' in source
    assert 'op.create_index("ix_irpf_records_user_id"' in source


def test_irpf_records_migration_preserves_shared_enum() -> None:
    source = _MIGRATION.read_text(encoding="utf-8").lower()

    assert "drop type" not in source
    assert "irpfmarket" in source
