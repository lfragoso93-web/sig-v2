"""Matriz financeira dos tipos de evento do pipeline de Proventos."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.dividend_backfill_service import (
    backfill_dividends,
    materialize_asset_dividends,
)


MONETARY_EVENTS = [
    pytest.param(DividendType.DIVIDENDO, "12.50000000", id="dividendo"),
    pytest.param(DividendType.JCP, "10.62500000", id="jcp"),
    pytest.param(DividendType.RENDIMENTO, "12.50000000", id="rendimento"),
    pytest.param(DividendType.AMORTIZACAO, "12.50000000", id="amortizacao"),
]

NON_MONETARY_EVENTS = [
    pytest.param(
        "EVBON3",
        "Bonificação",
        "stock",
        DividendType.BONIFICACAO,
        id="bonificacao",
    ),
    pytest.param(
        "EVSUB3",
        "Subscrição",
        "subscription",
        DividendType.SUBSCRICAO,
        id="subscricao",
    ),
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ticker,label,category,event_type",
    NON_MONETARY_EVENTS,
)
async def test_collects_non_monetary_event_without_financial_materialization(
    db: AsyncSession,
    portfolio: Portfolio,
    ticker: str,
    label: str,
    category: str,
    event_type: DividendType,
):
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker=ticker,
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("10"),
            price=Decimal("100"),
            date=date(2026, 1, 2),
        )
    )
    await db.flush()
    raw_events = [
        {
            "lastDatePrior": "2026-01-09",
            "approvedOn": "2026-01-05",
            "label": label,
            "eventCategory": category,
            "factor": 0.10,
            "completeFactor": 1.10,
        }
    ]

    with patch(
        "app.services.dividend_backfill_service._fetch_dividends_brapi",
        new_callable=AsyncMock,
        return_value=raw_events,
    ):
        await backfill_dividends(db, portfolio.id, ticker, "ACAO")

    event = (
        await db.execute(
            select(AssetDividend)
            .join(Asset, AssetDividend.asset_id == Asset.id)
            .where(Asset.ticker == ticker)
        )
    ).scalar_one()
    rights = (await db.execute(select(Dividend))).scalars().all()

    assert event.dividend_type == event_type
    assert event.value_per_unit == Decimal("0E-8")
    assert event.factor == Decimal("0.100000000000")
    assert event.complete_factor == Decimal("1.100000000000")
    assert rights == []
