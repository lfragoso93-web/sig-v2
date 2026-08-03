from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.performance_service import get_portfolio_performance
from sqlalchemy.ext.asyncio import AsyncSession

CANONICAL_ZERO = {
    "total_invested": 0.0,
    "current_value": 0.0,
    "total_gain": 0.0,
    "total_gain_pct": 0.0,
}


@pytest.mark.asyncio
async def test_get_portfolio_performance_no_transactions():
    db = AsyncMock(spec=AsyncSession)

    with (
        patch("app.services.performance_service.calc_raw_positions") as mock_positions,
        patch(
            "app.services.performance_service.get_canonical_portfolio_summary"
        ) as mock_summary,
    ):
        mock_positions.return_value = []
        mock_summary.return_value = CANONICAL_ZERO

        result = await get_portfolio_performance(db, portfolio_id=1, user_id=1)

        assert result["total_invested"] == 0.0
        assert result["total_current_value"] == 0.0
        assert result["total_gain"] == 0.0
        assert result["total_gain_pct"] == 0.0
        assert result["positions"] == []
        mock_positions.assert_awaited_once_with(db, 1)
        mock_summary.assert_awaited_once_with(db, 1, 1)


@pytest.mark.asyncio
async def test_get_portfolio_performance_single_stock_uses_canonical_totals():
    db = AsyncMock(spec=AsyncSession)

    mock_asset = MagicMock()
    mock_asset.name = "Vale S.A."
    mock_asset.ticker = "VALE3"

    canonical = {
        "total_invested": 7000.0,
        "current_value": 8100.0,
        "total_gain": 1100.0,
        "total_gain_pct": 15.7143,
    }

    with (
        patch("app.services.performance_service.calc_raw_positions") as mock_positions,
        patch("app.services.performance_service.get_current_price") as mock_get_price,
        patch(
            "app.services.performance_service.get_canonical_portfolio_summary"
        ) as mock_summary,
    ):
        mock_positions.return_value = [
            {
                "ticker": "VALE3",
                "asset_type": "STOCK",
                "quantity": 100.0,
                "total_invested": 5010.0,
            }
        ]
        mock_get_price.return_value = 60.0
        mock_summary.return_value = canonical

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = mock_asset
        db.execute.return_value = asset_result

        result = await get_portfolio_performance(db, portfolio_id=1, user_id=1)

        assert result["total_invested"] == 7000.0
        assert result["total_current_value"] == 8100.0
        assert result["total_gain"] == 1100.0
        assert result["total_gain_pct"] == 15.7143
        assert len(result["positions"]) == 1
        assert result["positions"][0]["ticker"] == "VALE3"
        assert result["positions"][0]["quantity"] == 100.0


@pytest.mark.asyncio
async def test_get_portfolio_performance_uses_projected_quantity_after_split():
    db = AsyncMock(spec=AsyncSession)

    mock_asset = MagicMock()
    mock_asset.name = "Petrobras"
    mock_asset.ticker = "PETR4"

    with (
        patch("app.services.performance_service.calc_raw_positions") as mock_positions,
        patch("app.services.performance_service.get_current_price") as mock_get_price,
        patch(
            "app.services.performance_service.get_canonical_portfolio_summary"
        ) as mock_summary,
    ):
        mock_positions.return_value = [
            {
                "ticker": "PETR4",
                "asset_type": "STOCK",
                "quantity": 300.0,
                "total_invested": 6020.0,
            }
        ]
        mock_get_price.return_value = 20.0
        mock_summary.return_value = CANONICAL_ZERO

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = mock_asset
        db.execute.return_value = asset_result

        result = await get_portfolio_performance(db, portfolio_id=1, user_id=1)

        assert len(result["positions"]) == 1
        assert result["positions"][0]["quantity"] == 300.0
        assert result["positions"][0]["invested"] == 6020.0
        assert result["positions"][0]["current_value"] == 6000.0


@pytest.mark.asyncio
async def test_get_portfolio_performance_zero_current_price():
    db = AsyncMock(spec=AsyncSession)

    mock_asset = MagicMock()
    mock_asset.name = "Test Asset"

    with (
        patch("app.services.performance_service.calc_raw_positions") as mock_positions,
        patch("app.services.performance_service.get_current_price") as mock_get_price,
        patch(
            "app.services.performance_service.get_canonical_portfolio_summary"
        ) as mock_summary,
    ):
        mock_positions.return_value = [
            {
                "ticker": "TEST1",
                "asset_type": "STOCK",
                "quantity": 100.0,
                "total_invested": 5000.0,
            }
        ]
        mock_get_price.return_value = None
        mock_summary.return_value = CANONICAL_ZERO

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = mock_asset
        db.execute.return_value = asset_result

        result = await get_portfolio_performance(db, portfolio_id=1, user_id=1)

        assert len(result["positions"]) == 1
        assert result["positions"][0]["current_value"] == 5000.0


@pytest.mark.asyncio
async def test_get_portfolio_performance_multiple_stocks():
    db = AsyncMock(spec=AsyncSession)

    mock_asset1 = MagicMock()
    mock_asset1.name = "Vale"

    mock_asset2 = MagicMock()
    mock_asset2.name = "Petrobras"

    canonical = {
        "total_invested": 11000.0,
        "current_value": 13000.0,
        "total_gain": 2000.0,
        "total_gain_pct": 18.1818,
    }

    with (
        patch("app.services.performance_service.calc_raw_positions") as mock_positions,
        patch("app.services.performance_service.get_current_price") as mock_get_price,
        patch(
            "app.services.performance_service.get_canonical_portfolio_summary"
        ) as mock_summary,
    ):
        mock_positions.return_value = [
            {
                "ticker": "VALE3",
                "asset_type": "STOCK",
                "quantity": 100.0,
                "total_invested": 5000.0,
            },
            {
                "ticker": "PETR4",
                "asset_type": "STOCK",
                "quantity": 200.0,
                "total_invested": 6000.0,
            },
        ]
        mock_get_price.side_effect = [60.0, 35.0]
        mock_summary.return_value = canonical

        asset_result1 = MagicMock()
        asset_result1.scalar_one_or_none.return_value = mock_asset1
        asset_result2 = MagicMock()
        asset_result2.scalar_one_or_none.return_value = mock_asset2
        db.execute.side_effect = [asset_result1, asset_result2]

        result = await get_portfolio_performance(db, portfolio_id=1, user_id=1)

        assert len(result["positions"]) == 2
        assert result["total_invested"] == 11000.0
        assert result["total_current_value"] == 13000.0
        assert result["total_gain"] == 2000.0
        assert result["total_gain_pct"] == 18.1818
