from app.main import app
from tests.route_tree_helpers import route_pairs


def test_admin_has_single_http_surface_for_broad_provider_ingestion() -> None:
    routes = route_pairs(app)

    assert ("POST", "/api/v1/admin/bootstrap") in routes
    assert ("GET", "/api/v1/admin/bootstrap/status") in routes

    assert ("POST", "/api/v1/admin/assets/seed") not in routes
    assert ("POST", "/api/v1/admin/prices/backfill") not in routes
    assert ("GET", "/api/v1/admin/prices/backfill/status") not in routes

    # Manutenção local/derivada permanece separada do bootstrap de providers.
    assert ("POST", "/api/v1/admin/snapshots/backfill") in routes
