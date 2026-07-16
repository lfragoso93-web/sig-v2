from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.portfolio_snapshot_read_service import (
    get_enriched_monthly_evolution,
    snapshot_to_enriched_payload,
)


def _snapshot(snapshot_date: date, daily_return: str = "0"):
    return SimpleNamespace(
        snapshot_date=snapshot_date,
        market_value=Decimal("1100.00"),
        cost_basis=Decimal("1000.00"),
        invested_total=Decimal("1000.00"),
        unrealized_pnl=Decimal("80.00"),
        realized_pnl=Decimal("20.00"),
        total_pnl=Decimal("100.00"),
        return_pct=Decimal("10.0000"),
        net_external_flow=Decimal("0.00"),
        dividends_day=Decimal("5.00"),
        dividends_accumulated=Decimal("50.00"),
        daily_return_pct=Decimal(daily_return),
        accumulated_return_pct=Decimal("10.500000"),
        has_partial_prices=True,
        return_is_estimated=True,
    )


def test_snapshot_payload_preserves_legacy_and_exposes_twr_fields():
    payload = snapshot_to_enriched_payload(
        _snapshot(date(2026, 7, 13), "1.250000"),
        include_monthly_aliases=True,
    )

    assert payload["market_value"] == 1100.0
    assert payload["return_pct"] == 10.0
    assert payload["daily_return_pct"] == 1.25
    assert payload["accumulated_return_pct"] == 10.5
    assert payload["dividends_accumulated"] == 50.0
    assert payload["has_partial_prices"] is True
    assert payload["return_is_estimated"] is True
    assert payload["period"] == "2026-07"


@pytest.mark.asyncio
async def test_monthly_evolution_compounds_daily_returns():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _snapshot(date(2026, 7, 1), "2.000000"),
        _snapshot(date(2026, 7, 2), "-1.000000"),
    ]
    db.execute.return_value = result

    payload = await get_enriched_monthly_evolution(db, portfolio_id=7, months=1)

    assert len(payload) == 1
    assert payload[0]["date"] == "2026-07-02"
    assert payload[0]["monthly_return_pct"] == 0.98
