from pathlib import Path

_ROUTER_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "performance.py"


def test_performance_router_has_no_public_backfill_endpoint() -> None:
    source = _ROUTER_PATH.read_text(encoding="utf-8")

    assert "evolution/backfill" not in source
    assert "@router.post" not in source


def test_performance_router_does_not_import_snapshot_rebuilders() -> None:
    source = _ROUTER_PATH.read_text(encoding="utf-8")

    assert "backfill_snapshots_with_returns" not in source
    assert "rebuild_class_snapshots" not in source
