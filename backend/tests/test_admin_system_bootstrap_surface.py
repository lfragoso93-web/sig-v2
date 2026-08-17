from pathlib import Path

from app.main import app
from app.routers import admin_bootstrap
from tests.route_tree_helpers import http_method_path_pairs


ROUTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin_bootstrap.py"
)

ADMIN_ROUTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin.py"
)


def test_admin_bootstrap_router_defines_expected_routes() -> None:
    routes = set(http_method_path_pairs(admin_bootstrap.router.routes))
    assert ("POST", "/bootstrap") in routes, sorted(routes)
    assert ("GET", "/bootstrap/status") in routes, sorted(routes)


def test_admin_bootstrap_routes_are_registered_once() -> None:
    pairs = http_method_path_pairs(app.routes)
    assert pairs.count(("POST", "/api/v1/admin/bootstrap")) == 1, sorted(pairs)
    assert pairs.count(("GET", "/api/v1/admin/bootstrap/status")) == 1, sorted(pairs)


def test_admin_bootstrap_router_delegates_only_to_global_bootstrap_boundary() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    assert "reserve_system_bootstrap_launch" in source
    assert "run_reserved_system_bootstrap" in source
    assert "get_bootstrap_readiness" in source
    assert "run_asset_seed" not in source
    assert "run_initial_backfill" not in source
    assert "brapi" not in source.lower()
    assert "yfinance" not in source.lower()


def test_legacy_bootstrap_routes_do_not_return_to_admin_router() -> None:
    source = ADMIN_ROUTER_PATH.read_text(encoding="utf-8")
    assert 'router.post("/bootstrap"' not in source
    assert 'router.get("/bootstrap/status"' not in source
    assert "enqueue_system_bootstrap" not in source
    assert "get_system_bootstrap_status" not in source
