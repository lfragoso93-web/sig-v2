from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import portfolio_summary_service
from app.services.portfolio_summary_service import _build_summary_from_valuation_fallback


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("missing_price", "expected_covered", "expected_coverage", "expected_missing"),
    [
        (False, 2, 100.0, []),
        (True, 1, 50.0, ["HGLG11"]),
    ],
    ids=["complete", "partial"],
)
async def test_summary_reports_complete_and_partial_price_coverage(
    monkeypatch,
    missing_price: bool,
    expected_covered: int,
    expected_coverage: float,
    expected_missing: list[str],
) -> None:
    enriched_positions = [
        {
            "ticker": "PETR4",
            "asset_type": "ACAO",
            "total_invested": 1_100.0,
            "current_value": 1_100.0,
            "current_price": 11.0,
        },
        {
            "ticker": "HGLG11",
            "asset_type": "FII",
            "total_invested": 900.0,
            "current_value": None if missing_price else 900.0,
            "current_price": None if missing_price else 90.0,
        },
    ]

    monkeypatch.setattr(
        portfolio_summary_service,
        "_non_fixed_income_enriched",
        AsyncMock(return_value=enriched_positions),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_fixed_income_totals",
        AsyncMock(
            return_value={
                "invested_amount": Decimal("3000.00"),
                "current_value": Decimal("3150.00"),
            }
        ),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "_get_received_dividend_totals",
        AsyncMock(return_value=(0.0, 0.0)),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_realized_pnl",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_usd_brl_today",
        AsyncMock(return_value=5.4),
    )

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: datetime(2026, 7, 18, 15, 30, tzinfo=timezone.utc),
    )

    summary = await _build_summary_from_valuation_fallback(db, 7)

    assert summary["total_investido"] == 5_000
    assert summary["total_patrimonio"] == 5_150
    assert summary["price_assets_total"] == 2
    assert summary["price_assets_covered"] == expected_covered
    assert summary["price_coverage_pct"] == expected_coverage
    assert summary["assets_without_price"] == expected_missing
    assert summary["has_partial_prices"] is missing_price
    assert summary["valuation_mode"] == "intraday"
    assert summary["summary_source"] == "valuation_fallback"
