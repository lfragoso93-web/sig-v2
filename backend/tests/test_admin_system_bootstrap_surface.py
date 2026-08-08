from pathlib import Path

from app.main import app
from app.routers import admin_bootstrap


ROUTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin_bootstrap.py"
)


def _route_pairs(routes) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in routes
        for method in getattr(route, "methods", set())
    }


def test_admin_bootstrap_router_defines_expected_routes() -> None:
    routes = _route_pairs(admin_bootstrap.router.routes)
    assert ("POST", "/bootstrap") in routes, sorted(routes)
    assert ("GET", "/bootstrap/status") in routes, sorted(routes)


def test_admin_bootstrap_routes_are_registered_once() -> None:
    routes = _route_pairs(app.routes)
    assert ("POST", "/api/v1/admin/bootstrap") in routes, sorted(routes)
    assert ("GET", "/api/v1/admin/bootstrap/status") in routes, sorted(routes)


def test_admin_bootstrap_router_delegates_only_to_global_bootstrap_boundary() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    assert "reserve_system_bootstrap_launch" in source
    assert "run_reserved_system_bootstrap" in source
    assert "get_bootstrap_readiness" in source
    assert "run_asset_seed" not in source
    assert "run_initial_backfill" not in source
    assert "brapi" not in source.lower()
    assert "yfinance" not in source.lower()
