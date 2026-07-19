"""Matriz financeira dos tipos de evento do pipeline de Proventos."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.dividend_backfill_service import materialize_asset_dividends


MONETARY_EVENTS = [
    pytest.param(DividendType.DIVIDENDO, "12.50000000", id="dividendo"),
    pytest.param(DividendType.JCP, "10.62500000", id="jcp"),
    pytest.param(DividendType.RENDIMENTO, "12.50000000", id="rendimento"),
    pytest.param(DividendType.AMORTIZACAO, "12.50000000", id="amortizacao"),
]


async def _asset_event_and_position(
    db: AsyncSession,
    portfolio_id: int,
    event_type: DividendType,
) -> AssetDividend:
    ticker = f"EV{event_type.value[:3]}3"
    asset = Asset(
        ticker=ticker,
        name=ticker,
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("10"),
            price=Decimal("100"),
            date=date(2026, 1, 2),
        )
    )
    event = AssetDividend(
        asset_id=asset.id,
        record_date=date(2026, 1, 9),
        ex_date=date(2026, 1, 12),
        payment_date=date(2026, 1, 30),
        value_per_unit=Decimal("1.25"),
        dividend_type=event_type,
        source="test",
    )
    db.add(event)
    await db.flush()
    return event


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type,expected_net", MONETARY_EVENTS)
async def test_materializes_expected_gross_and_net_values(
    db: AsyncSession,
    portfolio: Portfolio,
    event_type: DividendType,
    expected_net: str,
):
    event = await _asset_event_and_position(db, portfolio.id, event_type)

    changed = await materialize_asset_dividends(
        db,
        portfolio_id=portfolio.id,
        commit=False,
    )

    right = (
        await db.execute(
            select(Dividend).where(Dividend.asset_dividend_id == event.id)
        )
    ).scalar_one()

    assert changed == 1
    assert right.dividend_type == event_type.value
    assert right.quantity == Decimal("10.00000000")
    assert right.value_per_unit == Decimal("1.25000000")
    assert right.total_value == Decimal("12.50000000")
    assert right.net_value == Decimal(expected_net)
