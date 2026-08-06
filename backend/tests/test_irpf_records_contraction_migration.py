"""Gates para a contração isolada de ``irpf_records``."""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = (
    _BACKEND_ROOT
    / "alembic"
    / "versions"
    / "20260806_drop_irpf_records.py"
)


def test_irpf_records_migration_is_isolated_and_guarded() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260806_drop_irpf_records"' in source
    assert 'down_revision: str = "20260806_drop_irpf_losses"' in source
    assert '_TABLE = "irpf_records"' in source
    assert "SELECT COUNT(*)" in source
    assert "physical contraction blocked" in source
    assert "op.drop_table(_TABLE)" in source
    assert "irpf_losses" not in source


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
