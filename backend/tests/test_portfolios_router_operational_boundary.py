from pathlib import Path

from app.main import app


PORTFOLIOS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "portfolios.py"
)


def test_public_portfolio_router_has_no_snapshot_backfill_endpoint() -> None:
    routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set()) or set()
    }
    assert (
        "POST",
        "/api/v1/portfolios/{portfolio_id}/snapshots/backfill",
    ) not in routes


def test_portfolios_router_does_not_duplicate_class_target_mutations() -> None:
    source = PORTFOLIOS_PATH.read_text(encoding="utf-8")
    assert '@router.put(\n    "/{portfolio_id}/class-targets/{asset_type}"' not in source
    assert '@router.delete(\n    "/{portfolio_id}/class-targets/{asset_type}"' not in source
    assert "upsert_target" not in source
    assert "delete_target" not in source
