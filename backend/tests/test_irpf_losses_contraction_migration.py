"""Gates para a contração isolada de ``irpf_losses``."""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = (
    _BACKEND_ROOT
    / "alembic"
    / "versions"
    / "20260806_drop_irpf_losses.py"
)


def test_irpf_losses_migration_is_isolated_and_guarded() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260806_drop_irpf_losses"' in source
    assert 'down_revision: str = "20260806_drop_goal_allocations"' in source
    assert '_TABLE = "irpf_losses"' in source
    assert "SELECT COUNT(*)" in source
    assert "physical contraction blocked" in source
    assert "op.drop_table(_TABLE)" in source
    assert "irpf_records" not in source


def test_irpf_losses_downgrade_restores_original_contract() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'name="irpfmarket"' in source
    assert "create_type=False" in source
    assert 'sa.ForeignKey("users.id", ondelete="CASCADE")' in source
    assert 'sa.Column("accumulated_loss",' in source
    assert 'op.create_index("ix_irpf_losses_id"' in source


def test_irpf_losses_migration_preserves_shared_enum() -> None:
    source = _MIGRATION.read_text(encoding="utf-8").lower()

    assert "drop type" not in source
    assert "irpfmarket" in source
