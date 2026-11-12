import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.models.asset import Asset, AssetType
from app.services.ibov_benchmark_service import sync_ibov_benchmark_prices


@pytest.mark.asyncio
async def test_sync_ibov_benchmark_prices_brapi():
    db = AsyncMock()
    fake_asset = Asset(
        id=999,
        ticker="IBOV",
        name="Ibovespa",
        asset_type=AssetType.OUTRO.value,
    )

    fake_rows = [
        {
            "timestamp": datetime(2026, 10, 22, tzinfo=timezone.utc),
            "close": Decimal("204000.50"),
            "source": "brapi_ibov",
        },
        {
            "timestamp": datetime(2026, 10, 23, tzinfo=timezone.utc),
            "close": Decimal("205000.00"),
            "source": "brapi_ibov",
        },
    ]

    with patch(
        "app.services.ibov_benchmark_service._ensure_ibov_benchmark_asset",
        return_value=fake_asset,
    ), patch(
        "app.services.ibov_benchmark_service._fetch_ibov_brapi",
        return_value=fake_rows,
    ):
        count = await sync_ibov_benchmark_prices(db, range_str="1mo", commit=True)
        assert count == 2
        assert db.execute.call_count == 2
        assert db.commit.call_count == 1
        assert fake_asset.last_price == 205000.00


@pytest.mark.asyncio
async def test_sync_ibov_benchmark_prices_expands_to_max_when_history_missing():
    db = AsyncMock()
    fake_asset = Asset(
        id=999,
        ticker="IBOV",
        name="Ibovespa",
        asset_type=AssetType.OUTRO.value,
    )
    yahoo_rows = [
        {
            "timestamp": datetime(1994, 7, 1, tzinfo=timezone.utc),
            "close": Decimal("3623.00"),
            "source": "yahoo_ibov",
        },
        {
            "timestamp": datetime(2026, 11, 12, tzinfo=timezone.utc),
            "close": Decimal("128500.00"),
            "source": "yahoo_ibov",
        },
    ]

    with patch(
        "app.services.ibov_benchmark_service._ensure_ibov_benchmark_asset",
        return_value=fake_asset,
    ), patch(
        "app.services.ibov_benchmark_service._has_full_ibov_history",
        return_value=False,
    ), patch(
        "app.services.ibov_benchmark_service._fetch_ibov_brapi",
        return_value=[],
    ) as mock_brapi, patch(
        "app.services.ibov_benchmark_service._fetch_ibov_yahoo",
        return_value=yahoo_rows,
    ) as mock_yahoo:
        count = await sync_ibov_benchmark_prices(
            db, range_str="1mo", ensure_full_history=True, commit=True
        )
        assert count == 2
        mock_brapi.assert_awaited_once_with(range_str="max")
        mock_yahoo.assert_called_once_with("max")
        assert fake_asset.last_price == 128500.00
