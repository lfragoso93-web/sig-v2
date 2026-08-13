from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import performance_service


def test_performance_service_uses_persisted_current_price_reader_only() -> None:
    source = inspect.getsource(performance_service)

    assert "app.services.quotes_service" not in source
    assert "get_current_price" not in source
    assert "get_persisted_current_prices" in source


@pytest.mark.asyncio
async def test_performance_uses_persisted_prices_in_one_batch() -> None:
    db = AsyncMock()
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = MagicMock(name="Vale")
    db.execute.return_value = asset_result

    with (
        patch.object(
            performance_service,
            "calc_raw_positions",
            return_value=[
                {
                    "ticker": "vale3",
                    "asset_type": "ACAO",
                    "quantity": 10.0,
                    "total_invested": 500.0,
                }
            ],
        ),
        patch.object(
            performance_service,
            "get_persisted_current_prices",
            return_value={"VALE3": 60.0},
            create=True,
        ) as persisted_reader,
        patch.object(
            performance_service,
            "get_canonical_portfolio_summary",
            return_value={
                "total_invested": 500.0,
                "current_value": 600.0,
                "total_gain": 100.0,
                "total_gain_pct": 20.0,
            },
        ),
    ):
        result = await performance_service.get_portfolio_performance(db, 1, 2)

    persisted_reader.assert_awaited_once_with(db, ["VALE3"])
    item = result["positions"][0]
    assert item["current_price"] == 60.0
    assert item["has_current_price"] is True
    assert item["current_value"] == 600.0


@pytest.mark.asyncio
async def test_performance_marks_missing_persisted_price_explicitly() -> None:
    db = AsyncMock()
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = None
    db.execute.return_value = asset_result

    with (
        patch.object(
            performance_service,
            "calc_raw_positions",
            return_value=[
                {
                    "ticker": "MISS3",
                    "asset_type": "ACAO",
                    "quantity": 10.0,
                    "total_invested": 500.0,
                }
            ],
        ),
        patch.object(
            performance_service,
            "get_persisted_current_prices",
            return_value={},
            create=True,
        ),
        patch.object(
            performance_service,
            "get_canonical_portfolio_summary",
            return_value={
                "total_invested": 500.0,
                "current_value": 500.0,
                "total_gain": 0.0,
                "total_gain_pct": 0.0,
            },
        ),
    ):
        result = await performance_service.get_portfolio_performance(db, 1, 2)

    item = result["positions"][0]
    assert item["current_price"] is None
    assert item["has_current_price"] is False
    assert item["current_value"] == 500.0
    assert item["gain"] == 0.0
