"""Gates para a contração isolada de goal_allocations."""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = (
    _BACKEND_ROOT
    / "alembic"
    / "versions"
    / "20260806_drop_goal_allocations.py"
)


def test_goal_allocations_contraction_is_isolated_and_guarded() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260806_drop_goal_allocations"' in source
    assert 'down_revision: str = "20260731_corp_event_catalog"' in source
    assert 'SELECT COUNT(*) FROM goal_allocations' in source
    assert 'op.drop_table("goal_allocations")' in source
    assert "irpf_records" not in source
    assert "irpf_losses" not in source


def test_goal_allocations_contraction_refuses_non_empty_table() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert "if row_count:" in source
    assert "physical contraction blocked" in source
    assert "preserve or migrate them before retrying" in source


def test_goal_allocations_downgrade_restores_original_contract() -> None:
    source = _MIGRATION.read_text(encoding="utf-8")

    assert 'op.create_table(\n        "goal_allocations"' in source
    assert 'sa.Column("goal_id", sa.Integer(), nullable=False)' in source
    assert 'sa.Column("asset_type", sa.String(length=30), nullable=False)' in source
    assert "sa.Numeric(precision=6, scale=3)" in source
    assert 'name="goal_allocations_goal_id_fkey"' in source
    assert 'ondelete="CASCADE"' in source
    assert '"ix_goal_allocations_id"' in source
