from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.routers import assets


def _asset(ticker: str = "PETR4", asset_type: str = "ACAO") -> MagicMock:
    asset = MagicMock()
    asset.id = 1
    asset.ticker = ticker
    asset.name = ticker
    asset.asset_type = asset_type
    asset.currency = "BRL"
    asset.last_price = None
    asset.last_price_updated_at = None
    return asset


@pytest.mark.asyncio
async def test_current_quote_uses_persisted_last_price() -> None:
    db = AsyncMock()
    catalog_asset = _asset()

    with (
        patch.object(assets, "_find_catalog_asset", return_value=catalog_asset),
        patch.object(
            assets,
            "get_persisted_current_prices",
            return_value={"PETR4": 31.5},
        ) as current_reader,
    ):
        result = await assets.get_ticker_quote("PETR4", None, None, db, None)

    current_reader.assert_awaited_once_with(db, ["PETR4"])
    assert result.price == 31.5
    assert result.source == "assets.last_price"


@pytest.mark.asyncio
async def test_historical_quote_uses_persisted_history_only() -> None:
    db = AsyncMock()
    catalog_asset = _asset()

    with (
        patch.object(assets, "_find_catalog_asset", return_value=catalog_asset),
        patch.object(
            assets,
            "get_persisted_prices_at_date_batch",
            return_value={"PETR4": 29.0},
        ) as history_reader,
    ):
        result = await assets.get_ticker_quote(
            "PETR4",
            "2026-08-01",
            None,
            db,
            None,
        )

    history_reader.assert_awaited_once()
    assert result.price == 29.0
    assert result.source == "asset_prices"


@pytest.mark.asyncio
async def test_treasury_current_price_uses_persisted_market_price() -> None:
    db = AsyncMock()
    catalog_asset = _asset("BRSTNCNTB0X", "TESOURO_DIRETO")
    today = datetime.now(timezone.utc).date().isoformat()

    with (
        patch.object(assets, "_find_catalog_asset", return_value=catalog_asset),
        patch.object(
            assets,
            "get_persisted_current_prices",
            return_value={"BRSTNCNTB0X": 4321.25},
        ),
    ):
        result = await assets.get_treasury_price(
            "BRSTNCNTB0X",
            today,
            db,
            None,
        )

    assert result.price == 4321.25
    assert result.source == "assets.last_price"


@pytest.mark.asyncio
async def test_asset_detail_exposes_persisted_date_price_history() -> None:
    db = AsyncMock()
    catalog_asset = _asset()

    with (
        patch.object(assets, "_find_catalog_asset", return_value=catalog_asset),
        patch.object(
            assets,
            "get_persisted_current_prices",
            return_value={"PETR4": 31.5},
        ),
        patch.object(
            assets,
            "get_persisted_price_history",
            return_value=[{"date": "2026-08-01", "price": 29.0}],
        ),
    ):
        result = await assets.get_asset_detail("PETR4", 90, db, None)

    assert result.current_price == 31.5
    assert result.price_history[0].date == "2026-08-01"
    assert result.price_history[0].price == 29.0
