from pathlib import Path

from app.main import app
from tests.route_tree_helpers import http_method_path_pairs


ADMIN_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin.py"
)


def test_admin_legacy_provider_bootstrap_ports_are_removed() -> None:
    source = ADMIN_PATH.read_text(encoding="utf-8")
    routes = set(http_method_path_pairs(app.routes))

    assert '"/assets/seed"' not in source
    assert '"/prices/backfill"' not in source
    assert '"/prices/backfill/status"' not in source
    assert "run_asset_seed" not in source
    assert "run_initial_backfill" not in source

    assert ("POST", "/api/v1/admin/assets/seed") not in routes
    assert ("POST", "/api/v1/admin/prices/backfill") not in routes
    assert ("GET", "/api/v1/admin/prices/backfill/status") not in routes


def test_admin_snapshot_maintenance_remains_separate_from_provider_bootstrap() -> None:
    source = ADMIN_PATH.read_text(encoding="utf-8")
    routes = set(http_method_path_pairs(app.routes))

    assert '"/snapshots/backfill"' in source
    assert '"/snapshots/backfill/{portfolio_id}"' in source
    assert ("POST", "/api/v1/admin/snapshots/backfill") in routes
    assert ("POST", "/api/v1/admin/snapshots/backfill/{portfolio_id}") in routes
