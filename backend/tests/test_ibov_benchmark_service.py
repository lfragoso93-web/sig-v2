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
