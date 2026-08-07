from pathlib import Path


ROUTER_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "assets.py"


def _source() -> str:
    return ROUTER_PATH.read_text(encoding="utf-8")


def test_assets_router_does_not_import_providers_directly() -> None:
    source = _source()
    forbidden = {
        "app.integrations",
        "yfinance",
        "fetch_ticker_suggestions",
        "fetch_crypto_suggestions",
        "fetch_treasury_list",
        "fetch_historical_price",
        "fetch_treasury_price_by_date",
        "fetch_asset_info",
    }
    findings = sorted(token for token in forbidden if token in source)
    assert findings == []


def test_catalog_endpoints_use_db_first_query_service() -> None:
    source = _source()
    assert "suggest_assets_from_catalog" in source
    assert "list_treasury_from_catalog" in source
    assert "db: AsyncSession = Depends(get_db)" in source


def test_historical_quote_paths_use_point_gap_resolver() -> None:
    source = _source()
    assert "resolve_price_at_date_gap" in source
    assert 'source = "asset_prices"' in source
    assert 'source = "market_data_provider"' in source
    assert "get_current_price" in source
