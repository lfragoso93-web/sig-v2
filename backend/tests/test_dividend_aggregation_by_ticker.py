from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.dividend_aggregation_service import sum_received_dividends_by_ticker


@pytest.mark.asyncio
async def test_received_dividends_by_ticker_normalizes_and_rounds_rows():
    rows = [
        SimpleNamespace(ticker="PETR4", total=Decimal("123.456")),
        SimpleNamespace(ticker="HGLG11", total=Decimal("80.1")),
    ]
    result = MagicMock()
    result.all.return_value = rows
    db = AsyncMock()
    db.execute.return_value = result

    totals = await sum_received_dividends_by_ticker(
        db,
        portfolio_id=7,
        tickers=["petr4", "PETR4", "hglg11"],
        as_of=date(2026, 7, 16),
    )

    assert totals == {"PETR4": 123.46, "HGLG11": 80.1}
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_received_dividends_by_ticker_skips_query_without_tickers():
    db = AsyncMock()

    totals = await sum_received_dividends_by_ticker(db, portfolio_id=7, tickers=[])

    assert totals == {}
    db.execute.assert_not_awaited()
