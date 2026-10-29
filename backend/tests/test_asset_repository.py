from unittest.mock import AsyncMock, MagicMock
import pytest
from app.models.asset import Asset
from app.repositories.asset_repository import (
    get_asset_by_id,
    get_asset_by_ticker,
    get_assets_by_tickers,
)


@pytest.mark.asyncio
async def test_get_asset_by_id_returns_asset():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    fake_asset = Asset(id=42, ticker="PETR4", asset_type="ACAO")
    mock_result.scalar_one_or_none.return_value = fake_asset
    mock_db.execute.return_value = mock_result

    asset = await get_asset_by_id(mock_db, 42)
    assert asset is fake_asset
    assert mock_db.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_asset_by_ticker_normalizes_case():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    fake_asset = Asset(id=10, ticker="VALE3", asset_type="ACAO")
    mock_result.scalar_one_or_none.return_value = fake_asset
    mock_db.execute.return_value = mock_result

    asset = await get_asset_by_ticker(mock_db, "  vale3 ")
    assert asset is fake_asset
    assert mock_db.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_assets_by_tickers_empty_avoids_db():
    mock_db = AsyncMock()
    assets = await get_assets_by_tickers(mock_db, [])
    assert assets == []
    assert mock_db.execute.call_count == 0


@pytest.mark.asyncio
async def test_get_assets_by_tickers_queries_normalized():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    fake_assets = [
        Asset(id=1, ticker="ITUB4", asset_type="ACAO"),
        Asset(id=2, ticker="BBDC4", asset_type="ACAO"),
    ]
    mock_result.scalars.return_value.all.return_value = fake_assets
    mock_db.execute.return_value = mock_result

    assets = await get_assets_by_tickers(mock_db, ["itub4", "bbdc4"])
    assert len(assets) == 2
    assert mock_db.execute.call_count == 1
