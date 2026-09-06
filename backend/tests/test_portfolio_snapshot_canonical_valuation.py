from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.services import portfolio_snapshot_service as snapshot_service


@pytest.mark.asyncio
async def test_snapshot_totals_delegate_to_canonical_valuation(monkeypatch):
    canonical = {
        "market_value": Decimal("38960.00"),
        "cost_basis": Decimal("37629.30"),
        "invested_total": Decimal("37998.00"),
        "realized_pnl": Decimal("450.80"),
        "unrealized_pnl": Decimal("1330.70"),
        "total_pnl": Decimal("1781.50"),
        "return_pct": Decimal("4.6764"),
        "fixed_income_invested": Decimal("5000.00"),
        "fixed_income_current": Decimal("5050.00"),
        "treasury_correction": Decimal("-50.00"),
    }
    valuation = AsyncMock(return_value=canonical)
    monkeypatch.setattr(
        snapshot_service,
        "calculate_canonical_portfolio_totals",
        valuation,
    )

    totals = await snapshot_service._calc_totals(None, 13, date(2026, 2, 28))

    valuation.assert_awaited_once_with(None, 13, date(2026, 2, 28))
    assert totals == {
        key: canonical[key] for key in snapshot_service._SNAPSHOT_TOTAL_FIELDS
    }
    assert "fixed_income_current" not in totals
    assert "treasury_correction" not in totals


def test_snapshot_service_has_no_parallel_price_resolution_engine():
    source = snapshot_service.__file__
    text = open(source, encoding="utf-8").read()

    assert "get_persisted_prices_at_date_batch" not in text
    assert "resolve_missing_snapshot_prices" not in text
    assert "SnapshotPriceRequirement" not in text
