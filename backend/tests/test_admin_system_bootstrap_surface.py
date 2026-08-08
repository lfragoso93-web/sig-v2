from pathlib import Path

from app.main import app


ROUTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin_bootstrap.py"
)


def test_admin_bootstrap_routes_are_registered_once() -> None:
    routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    assert ("POST", "/api/v1/admin/bootstrap") in routes
    assert ("GET", "/api/v1/admin/bootstrap/status") in routes


def test_admin_bootstrap_router_delegates_only_to_global_bootstrap_boundary() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    assert "reserve_system_bootstrap_launch" in source
    assert "run_reserved_system_bootstrap" in source
    assert "get_bootstrap_readiness" in source
    assert "run_asset_seed" not in source
    assert "run_initial_backfill" not in source
    assert "brapi" not in source.lower()
    assert "yfinance" not in source.lower()
