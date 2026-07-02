"""Testes para asset_service — gerenciamento de ativos."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_service import (
    get_or_create_asset,
    list_assets,
    get_asset_by_ticker,
    search_assets,
)
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate


@pytest.mark.asyncio
class TestGetOrCreateAsset:

    async def test_get_existing_asset(self):
        db = AsyncMock(spec=AsyncSession)
        
        existing_asset = MagicMock(spec=Asset)
        existing_asset.ticker = "PETR4"
        existing_asset.name = "Petrobras"
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=existing_asset)
        db.execute = AsyncMock(return_value=execute_result)
        
        data = AssetCreate(
            ticker="PETR4",
            name="Petrobras",
            asset_type=AssetType.ACAO,
        )
        
        asset, is_new = await get_or_create_asset(db, data)
        
        assert asset == existing_asset
        assert is_new is False

    async def test_create_new_asset(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = AssetCreate(
            ticker="VALE3",
            name="Vale S.A.",
            asset_type=AssetType.ACAO,
        )
        
        asset, is_new = await get_or_create_asset(db, data)
        
        assert is_new is True
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    async def test_create_asset_with_currency(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = AssetCreate(
            ticker="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.STOCK,
            currency="USD",
        )
        
        asset, is_new = await get_or_create_asset(db, data)
        
        assert is_new is True


@pytest.mark.asyncio
class TestListAssets:

    async def test_list_assets_empty(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await list_assets(db)
        
        assert assets == []

    async def test_list_assets_multiple(self):
        db = AsyncMock(spec=AsyncSession)
        
        asset1 = MagicMock(spec=Asset)
        asset1.ticker = "PETR4"
        
        asset2 = MagicMock(spec=Asset)
        asset2.ticker = "VALE3"
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[asset1, asset2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await list_assets(db)
        
        assert len(assets) == 2
        assert assets[0].ticker == "PETR4"
        assert assets[1].ticker == "VALE3"


@pytest.mark.asyncio
class TestGetAssetByTicker:

    async def test_get_asset_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        asset = MagicMock(spec=Asset)
        asset.ticker = "PETR4"
        asset.name = "Petrobras"
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=asset)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_asset_by_ticker(db, "PETR4")
        
        assert result == asset

    async def test_get_asset_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_asset_by_ticker(db, "NONEXISTENT")
        
        assert result is None


@pytest.mark.asyncio
class TestSearchAssets:

    async def test_search_assets_empty_query(self):
        db = AsyncMock(spec=AsyncSession)
        
        asset1 = MagicMock(spec=Asset)
        asset1.ticker = "PETR4"
        
        asset2 = MagicMock(spec=Asset)
        asset2.ticker = "VALE3"
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[asset1, asset2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await search_assets(db, "")
        
        assert len(assets) == 2

    async def test_search_assets_by_ticker(self):
        db = AsyncMock(spec=AsyncSession)
        
        asset = MagicMock(spec=Asset)
        asset.ticker = "PETR4"
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[asset])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await search_assets(db, "PETR")
        
        assert len(assets) == 1
        assert assets[0].ticker == "PETR4"

    async def test_search_assets_by_name(self):
        db = AsyncMock(spec=AsyncSession)
        
        asset = MagicMock(spec=Asset)
        asset.ticker = "PETR4"
        asset.name = "Petrobras S.A."
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[asset])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await search_assets(db, "Petrobras")
        
        assert len(assets) == 1

    async def test_search_assets_by_type(self):
        db = AsyncMock(spec=AsyncSession)
        
        asset = MagicMock(spec=Asset)
        asset.ticker = "PETR4"
        asset.asset_type = AssetType.ACAO
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[asset])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await search_assets(db, "PETR", asset_type=AssetType.ACAO)
        
        assert len(assets) == 1

    async def test_search_assets_limit(self):
        db = AsyncMock(spec=AsyncSession)
        
        assets_list = [MagicMock(spec=Asset) for _ in range(5)]
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=assets_list[:10])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        assets = await search_assets(db, "", limit=10)
        
        assert len(assets) <= 10
