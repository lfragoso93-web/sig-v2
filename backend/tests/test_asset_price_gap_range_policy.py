import asyncio
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from app.models.asset import AssetType
from app.services.asset_price_gap_sync_service import MissingPriceRange, _fetch_range


def test_brapi_uses_range_max_for_initial_stock_history() -> None:
    expected = [(datetime(2020, 1, 2, tzinfo=timezone.utc), 10.0)]
    with patch(
        "app.integrations.brapi.fetch_stocks_historical_v2",
        new=AsyncMock(return_value=expected),
    ) as fetch:
        rows, source, terminal_status, provider = asyncio.run(
            _fetch_range(
                "PETR4",
                AssetType.ACAO,
                MissingPriceRange(date(1900, 1, 1), date(2026, 7, 14), "missing_start"),
            )
        )

    fetch.assert_awaited_once_with(ticker="PETR4", range_="max")
    assert rows == expected
    assert source == "brapi_v2_stocks_max"
    assert terminal_status is None
    assert provider == "brapi"


def test_fii_keeps_documented_date_window() -> None:
    expected = [(datetime(2025, 1, 2, tzinfo=timezone.utc), 9.5)]
    with patch(
        "app.integrations.brapi.fetch_fii_historical_v2",
        new=AsyncMock(return_value=expected),
    ) as fetch:
        rows, source, terminal_status, provider = asyncio.run(
            _fetch_range(
                "MXRF11",
                AssetType.FII,
                MissingPriceRange(date(2025, 1, 1), date(2026, 7, 14), "missing_start"),
            )
        )

    fetch.assert_awaited_once_with(
        ticker="MXRF11",
        date_from="2025-01-01",
        date_to="2026-07-14",
    )
    assert rows == expected
    assert source == "brapi_v2_fii"
    assert terminal_status is None
    assert provider == "brapi"


def test_yfinance_uses_period_max_for_initial_international_history() -> None:
    expected = [(datetime(2020, 1, 2, tzinfo=timezone.utc), 100.0)]
    with patch(
        "app.services.asset_price_gap_sync_service._fetch_yf_max",
        new=AsyncMock(return_value=expected),
    ) as fetch:
        rows, source, terminal_status, provider = asyncio.run(
            _fetch_range(
                "NVDA",
                AssetType.STOCK,
                MissingPriceRange(date(1900, 1, 1), date(2026, 7, 14), "missing_all"),
            )
        )

    fetch.assert_awaited_once_with("NVDA", AssetType.STOCK)
    assert rows == expected
    assert source == "yfinance_period_max"
    assert terminal_status is None
    assert provider == "yfinance"
