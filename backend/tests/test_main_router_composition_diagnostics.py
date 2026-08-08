from pathlib import Path

from fastapi import FastAPI

import app.main as main_module
from app.routers import auth
from app.routers.admin_bootstrap import router as admin_bootstrap_router
from tests.route_tree_helpers import http_method_path_pairs


EXPECTED_MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"


def test_main_module_resolves_to_container_source_tree() -> None:
    actual = Path(main_module.__file__).resolve()
    assert actual == EXPECTED_MAIN.resolve(), (actual, EXPECTED_MAIN.resolve())


def test_known_routers_are_populated_before_composition() -> None:
    auth_routes = http_method_path_pairs(auth.router.routes)
    bootstrap_routes = set(http_method_path_pairs(admin_bootstrap_router.routes))
    assert auth_routes, auth_routes
    assert ("POST", "/bootstrap") in bootstrap_routes, bootstrap_routes
    assert ("GET", "/bootstrap/status") in bootstrap_routes, bootstrap_routes


def test_fastapi_include_router_works_in_fresh_application() -> None:
    probe = FastAPI()
    probe.include_router(admin_bootstrap_router, prefix="/api/v1/admin")
    routes = set(http_method_path_pairs(probe.routes))
    assert ("POST", "/api/v1/admin/bootstrap") in routes, sorted(routes)
    assert ("GET", "/api/v1/admin/bootstrap/status") in routes, sorted(routes)


def test_real_main_application_keeps_business_routes() -> None:
    routes = set(http_method_path_pairs(main_module.app.routes))
    expected = {
        ("POST", "/api/v1/admin/bootstrap"),
        ("GET", "/api/v1/admin/bootstrap/status"),
    }
    missing = expected - routes
    assert not missing, {
        "missing": sorted(missing),
        "routes": sorted(routes),
        "main_file": str(Path(main_module.__file__).resolve()),
    }
