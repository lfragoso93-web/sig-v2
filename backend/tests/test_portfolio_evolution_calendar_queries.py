from datetime import date
from decimal import Decimal

import pytest

from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services import portfolio_class_snapshot_read_service as class_read_service
from app.services import portfolio_snapshot_read_service as portfolio_read_service


def portfolio_snapshot(portfolio_id: int, snapshot_date: date) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        market_value=Decimal("1200.00"),
        cost_basis=Decimal("1000.00"),
        invested_total=Decimal("1000.00"),
        realized_pnl=Decimal("0.00"),
        unrealized_pnl=Decimal("200.00"),
        total_pnl=Decimal("200.00"),
        return_pct=Decimal("20.0000"),
        net_external_flow=Decimal("0.00"),
        dividends_day=Decimal("0.00"),
        dividends_accumulated=Decimal("0.00"),
        daily_return_pct=Decimal("1.000000"),
        accumulated_return_pct=Decimal("5.000000"),
        has_partial_prices=False,
        return_is_estimated=False,
    )


def class_snapshot(portfolio_id: int, snapshot_date: date) -> PortfolioClassSnapshot:
    return PortfolioClassSnapshot(
        portfolio_id=portfolio_id,
        asset_type="ACAO",
        snapshot_date=snapshot_date,
        market_value=Decimal("1200.00"),
        cost_basis=Decimal("1000.00"),
        realized_pnl=Decimal("0.00"),
        unrealized_pnl=Decimal("200.00"),
        net_external_flow=Decimal("0.00"),
        dividends_day=Decimal("0.00"),
        dividends_accumulated=Decimal("0.00"),
        daily_return_pct=Decimal("1.000000"),
        accumulated_return_pct=Decimal("5.000000"),
        has_partial_prices=False,
        return_is_estimated=True,
        valuation_status="complete",
    )


@pytest.mark.asyncio
async def test_consolidated_monthly_query_uses_calendar_boundary(db, portfolio, monkeypatch) -> None:
    monkeypatch.setattr(
        portfolio_read_service,
        "monthly_window_start",
        lambda months: date(2026, 2, 1),
    )
    db.add_all([
        portfolio_snapshot(portfolio.id, date(2026, 1, 31)),
        portfolio_snapshot(portfolio.id, date(2026, 2, 1)),
    ])
    await db.flush()

    rows = await portfolio_read_service.get_enriched_monthly_evolution(
        db, portfolio.id, months=6
    )

    assert [row["period"] for row in rows] == ["2026-02"]


@pytest.mark.asyncio
async def test_class_monthly_query_uses_same_calendar_boundary(db, portfolio, monkeypatch) -> None:
    monkeypatch.setattr(
        class_read_service,
        "monthly_window_start",
        lambda months: date(2026, 2, 1),
    )
    db.add_all([
        class_snapshot(portfolio.id, date(2026, 1, 31)),
        class_snapshot(portfolio.id, date(2026, 2, 1)),
    ])
    await db.flush()

    rows = await class_read_service.get_monthly_class_evolution(
        db, portfolio.id, "ACAO", months=6
    )

    assert [row["period"] for row in rows] == ["2026-02"]
