from unittest.mock import AsyncMock, patch

import pytest

from app.services.canonical_positions_service import (
    build_canonical_group_metrics,
    get_canonical_portfolio_positions,
)


def test_group_metrics_separate_capital_result_from_received_dividends():
    metrics = build_canonical_group_metrics(
        total_value=9_000,
        total_invested=10_000,
        received_dividends=350,
    )

    assert metrics == {
        "capital_result_value": -1_000,
        "capital_result_pct": -10.0,
        "received_dividends": 350,
        "total_result_value": -650,
        "total_result_pct": -6.5,
    }


def test_group_metrics_support_zero_invested_without_fake_percentage():
    metrics = build_canonical_group_metrics(
        total_value=0,
        total_invested=0,
        received_dividends=100,
    )

    assert metrics["capital_result_pct"] is None
    assert metrics["total_result_pct"] is None


@pytest.mark.asyncio
async def test_positions_remove_legacy_return_and_use_received_dividends():
    legacy = [
        {
            "label": "Ações",
            "total_value": 9_000,
            "total_invested": 10_000,
            "daily_variation_pct": 1.25,
            "rentabilidade_pct": 99.9,
            "positions": [{"ticker": "PETR4"}, {"ticker": "VALE3"}],
        }
    ]

    with (
        patch(
            "app.services.canonical_positions_service.get_portfolio_positions",
            new=AsyncMock(return_value=legacy),
        ),
        patch(
            "app.services.canonical_positions_service.sum_received_dividends_by_ticker",
            new=AsyncMock(return_value={"PETR4": 200, "VALE3": 150}),
        ),
    ):
        groups = await get_canonical_portfolio_positions(AsyncMock(), 7, 3)

    group = groups[0]
    assert "rentabilidade_pct" not in group
    assert group["daily_variation_pct"] == 1.25
    assert group["capital_result_pct"] == -10.0
    assert group["received_dividends"] == 350
    assert group["total_result_pct"] == -6.5
    assert group["performance_source"] == "intraday_valuation_and_received_dividends"
