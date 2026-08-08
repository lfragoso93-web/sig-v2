from pathlib import Path


ADMIN_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin.py"
)


def test_admin_legacy_provider_bootstrap_ports_are_tracked() -> None:
    """Caracteriza as portas que o proximo commit deve consolidar."""
    source = ADMIN_PATH.read_text(encoding="utf-8")
    assert '@router.post(\n    "/assets/seed"' in source
    assert '@router.post(\n    "/prices/backfill"' in source
    assert "run_asset_seed" in source
    assert "run_initial_backfill" in source


def test_admin_snapshot_maintenance_remains_separate_from_provider_bootstrap() -> None:
    source = ADMIN_PATH.read_text(encoding="utf-8")
    assert '"/snapshots/backfill"' in source
    assert '"/snapshots/backfill/{portfolio_id}"' in source
