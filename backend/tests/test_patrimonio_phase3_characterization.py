from datetime import date
from decimal import Decimal

import pytest

from app.models.portfolio import Portfolio
from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.transaction import OperationType, Transaction
from app.services.portfolio_class_snapshot_read_service import (
    get_class_twr_availability,
    get_daily_class_evolution,
    get_monthly_class_evolution,
)


def class_snapshot(portfolio_id: int, snapshot_date: date, **overrides):
    values = {
        "portfolio_id": portfolio_id,
        "asset_type": "ACAO",
        "snapshot_date": snapshot_date,
        "market_value": Decimal("1200.00"),
        "cost_basis": Decimal("1000.00"),
        "realized_pnl": Decimal("50.00"),
        "unrealized_pnl": Decimal("200.00"),
        "net_external_flow": Decimal("0.00"),
        "dividends_day": Decimal("0.00"),
        "dividends_accumulated": Decimal("80.00"),
        "daily_return_pct": Decimal("1.000000"),
        "accumulated_return_pct": Decimal("8.000000"),
        "has_partial_prices": False,
        "return_is_estimated": True,
        "valuation_status": "complete",
    }
    values.update(overrides)
    return PortfolioClassSnapshot(**values)


@pytest.mark.asyncio
async def test_daily_class_evolution_isolated_by_portfolio(db, portfolio):
    other = Portfolio(user_id=portfolio.user_id, name="Outra", description="")
    db.add(other)
    await db.flush()
    db.add_all([
        class_snapshot(portfolio.id, date(2026, 1, 31)),
        class_snapshot(other.id, date(2026, 1, 31), market_value=Decimal("9999.00")),
    ])
    await db.flush()

    rows = await get_daily_class_evolution(db, portfolio.id, "acao", days=0)

    assert len(rows) == 1
    assert rows[0]["market_value"] == 1200.0
    assert rows[0]["history_source"] == "portfolio_class_snapshot"


@pytest.mark.asyncio
async def test_monthly_class_evolution_uses_last_close_and_compounds_daily_twr(db, portfolio):
    db.add_all([
        class_snapshot(portfolio.id, date(2026, 1, 30), daily_return_pct=Decimal("1.000000")),
        class_snapshot(
            portfolio.id,
            date(2026, 1, 31),
            market_value=Decimal("1250.00"),
            daily_return_pct=Decimal("2.000000"),
        ),
    ])
    await db.flush()

    rows = await get_monthly_class_evolution(db, portfolio.id, "ACAO", months=0)

    assert rows[0]["period"] == "2026-01"
    assert rows[0]["date"] == "2026-01-31"
    assert rows[0]["market_value"] == 1250.0
    assert rows[0]["monthly_return_pct"] == pytest.approx(3.02)


@pytest.mark.asyncio
async def test_class_availability_requires_supported_engine_and_materialized_data(db, portfolio):
    db.add_all([
        Transaction(
            portfolio_id=portfolio.id, ticker="PETR4", asset_type="ACAO",
            operation=OperationType.buy, quantity=1, price=10, date=date(2026, 1, 2),
        ),
        Transaction(
            portfolio_id=portfolio.id, ticker="TESOURO IPCA+ 2035", asset_type="TESOURO_DIRETO",
            operation=OperationType.buy, quantity=1, price=1000, date=date(2026, 1, 2),
        ),
        class_snapshot(portfolio.id, date(2026, 1, 31)),
    ])
    await db.flush()

    rows = await get_class_twr_availability(db, portfolio.id)
    by_type = {row["asset_type"]: row for row in rows}

    assert by_type["ACAO"]["available"] is True
    assert by_type["ACAO"]["latest_snapshot_date"] == "2026-01-31"
    assert by_type["TESOURO_DIRETO"]["available"] is False
    assert by_type["TESOURO_DIRETO"]["engine_supported"] is False
