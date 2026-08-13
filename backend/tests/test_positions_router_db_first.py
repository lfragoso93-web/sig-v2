from pathlib import Path

_ROUTER_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "positions.py"


def test_positions_router_has_no_refresh_query_contract() -> None:
    source = _ROUTER_PATH.read_text(encoding="utf-8")

    assert "refresh:" not in source
    assert "refresh =" not in source


def test_positions_router_does_not_trigger_quote_updates() -> None:
    source = _ROUTER_PATH.read_text(encoding="utf-8")

    assert "update_quotes_for_portfolio" not in source
    assert "quotes_service" not in source
