from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetType
from app.services.asset_catalog_query_service import (
    _normalize_filter,
    _user_selectable_catalog_predicate,
)


SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "asset_catalog_query_service.py"
)


def test_catalog_aliases_map_to_persisted_asset_types() -> None:
    assert _normalize_filter("cripto") == (AssetType.CRIPTO.value,)
    assert _normalize_filter("stock_int") == (AssetType.STOCK.value,)
    assert _normalize_filter("etf_int") == (AssetType.ETF_INTERNACIONAL.value,)
    assert _normalize_filter("tesouro") == (AssetType.TESOURO_DIRETO.value,)


def test_catalog_query_service_has_no_provider_dependencies() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    forbidden = {
        "app.integrations",
        "yfinance",
        "fetch_ticker_suggestions",
        "fetch_crypto_suggestions",
        "fetch_treasury_list",
        "fetch_asset_info",
    }
    findings = sorted(token for token in forbidden if token in source)
    assert findings == []


def test_catalog_query_is_read_only() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    forbidden = {"commit()", "flush()", "add(", "delete(", "update("}
    findings = sorted(token for token in forbidden if token in source)
    assert findings == []


def test_crypto_catalog_visibility_is_not_gated_by_market_history_status() -> None:
    sql = str(
        _user_selectable_catalog_predicate().compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    assert "provider_status" not in sql
    assert "synthetic-certification" in sql


@pytest.mark.asyncio
async def test_assets_only_respond_to_search_and_quotes_within_their_own_class(
    db: AsyncSession,
) -> None:
    from app.models.asset import Asset
    from app.routers.assets import _find_catalog_asset
    from app.services.asset_catalog_query_service import suggest_assets_from_catalog
    from app.services.asset_provider_verification_service import verify_market_asset_exists
    from app.services.asset_service import search_assets
    from app.services.persisted_current_price_query_service import get_persisted_current_prices

    assert _normalize_filter("STOCK") == (AssetType.STOCK.value,)
    assert _normalize_filter("ACAO") == (AssetType.ACAO.value,)

    db.add_all([
        Asset(ticker="AAPL", name="Apple Inc.", asset_type=AssetType.STOCK.value, currency="USD", last_price=220.0),
        Asset(ticker="PETR4", name="Petrobras PN", asset_type=AssetType.ACAO.value, currency="BRL", last_price=36.0),
        Asset(ticker="BTC", name="Bitcoin", asset_type=AssetType.CRIPTO.value, currency="BRL", last_price=400000.0),
        Asset(ticker="BTC", name="BTC", asset_type=AssetType.ACAO.value, currency="BRL", last_price=None),
        Asset(ticker="DIA", name="DIA Crypto", asset_type=AssetType.CRIPTO.value, currency="BRL", last_price=0.72),
        Asset(ticker="DIA", name="SPDR Dow Jones", asset_type=AssetType.ETF_INTERNACIONAL.value, currency="USD", last_price=524.0),
    ])
    await db.flush()

    stock_suggestions = await suggest_assets_from_catalog(db, "AAPL", asset_type="STOCK")
    assert [(s.ticker, s.asset_type) for s in stock_suggestions] == [("AAPL", "STOCK")]
    assert await suggest_assets_from_catalog(db, "AAPL", asset_type="ACAO") == []

    # BTC / Bitcoin never responds inside ACAO
    assert await suggest_assets_from_catalog(db, "BTC", asset_type="ACAO") == []
    assert await suggest_assets_from_catalog(db, "BITCOIN", asset_type="ACAO") == []
    assert [(s.ticker, s.asset_type) for s in await suggest_assets_from_catalog(db, "BITCOIN", asset_type="CRIPTO")] == [("BTC", "CRIPTO")]

    # /assets/search isolates classes strictly
    assert await search_assets(db, "BTC", asset_type=AssetType.ACAO) == []
    assert [(a.ticker, a.asset_type) for a in await search_assets(db, "BTC", asset_type=AssetType.CRIPTO)] == [("BTC", "CRIPTO")]

    # Quote lookup & persisted current prices stay scoped to asset_type
    assert await _find_catalog_asset(db, "AAPL", "ACAO") is None
    assert await _find_catalog_asset(db, "BITCOIN", "ACAO") is None
    assert await get_persisted_current_prices(db, ["DIA"], asset_type="CRIPTO") == {"DIA": 0.72}
    assert await get_persisted_current_prices(db, ["DIA"], asset_type="ETF_INTERNACIONAL") == {"DIA": 524.0}
    assert await get_persisted_current_prices(db, ["BTC"], asset_type="ACAO") == {}

    # Market asset verification blocks non-B3 ticker shapes like BTC in ACAO
    exists, name = await verify_market_asset_exists("BTC", "ACAO")
    assert exists is False and name is None
