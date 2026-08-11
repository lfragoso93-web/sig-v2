from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_MIGRATION = ROOT / "alembic" / "versions" / "20260811_asset_universe_memberships.py"
SOURCE64_MIGRATION = ROOT / "alembic" / "versions" / "20260811_asset_universe_source64.py"


def test_asset_universe_membership_migration_is_chained_and_reversible() -> None:
    source = BASE_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260811_asset_universe_map"' in source
    assert len("20260811_asset_universe_map") <= 32
    assert 'down_revision: str = "20260807_pos_snap_ts_nn"' in source
    assert '"asset_universe_memberships"' in source
    assert '"uq_asset_universe_membership_asset_universe"' in source
    assert '"ix_asset_universe_memberships_universe_rank"' in source
    assert 'op.drop_table("asset_universe_memberships")' in source


def test_asset_universe_membership_source_width_is_migrated_to_64() -> None:
    source = SOURCE64_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260811_asset_univ_source64"' in source
    assert len("20260811_asset_univ_source64") <= 32
    assert 'down_revision: str = "20260811_asset_universe_map"' in source
    assert '"asset_universe_memberships"' in source
    assert '"source"' in source
    assert "type_=sa.String(length=64)" in source
    assert "type_=sa.String(length=32)" in source
