from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260811_asset_universe_memberships.py"
)


def test_asset_universe_membership_migration_is_chained_and_reversible() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260811_asset_universe_memberships"' in source
    assert 'down_revision: str = "20260807_pos_snap_ts_nn"' in source
    assert '"asset_universe_memberships"' in source
    assert '"uq_asset_universe_membership_asset_universe"' in source
    assert '"ix_asset_universe_memberships_universe_rank"' in source
    assert 'op.drop_table("asset_universe_memberships")' in source
