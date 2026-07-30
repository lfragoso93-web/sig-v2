"""Matriz ponta a ponta das classes nacionais com Proventos."""

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


NATIONAL_DIVIDEND_CLASSES = [
    pytest.param("PETR4", "ACAO", "Dividendos", DividendType.DIVIDENDO, id="acao"),
    pytest.param("MXRF11", "FII", "Rendimentos", DividendType.RENDIMENTO, id="fii"),
    pytest.param(
        "BOVA11",
        "ETF_NACIONAL",
        "Dividendos",
        DividendType.DIVIDENDO,
        id="etf-nacional",
    ),
    pytest.param("AAPL34", "BDR", "Dividendos", DividendType.DIVIDENDO, id="bdr"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ticker,asset_type,label,expected_type",
    NATIONAL_DIVIDEND_CLASSES,
)
async def test_global_collection_does_not_require_portfolio_position(
    db: AsyncSession,
    ticker: str,
    asset_type: str,
    label: str,
    expected_type: DividendType,
):
    raw_events = [
        {
            "lastDatePrior": "2026-01-09",
            "paymentDate": "2026-01-30",
            "rate": 1.25,
            "label": label,
            "eventCategory": "cash",
        }
    ]

    with patch(
        "app.services.dividend_backfill_service._fetch_dividends_brapi",
        new_callable=AsyncMock,
        return_value=raw_events,
    ):
        await backfill_dividends(db, ticker, asset_type)

    event = (
        await db.execute(
            select(AssetDividend)
            .join(Asset, AssetDividend.asset_id == Asset.id)
            .where(Asset.ticker == ticker, Asset.asset_type == asset_type)
        )
    ).scalar_one()
    rights = (await db.execute(select(Dividend))).scalars().all()

    assert event.record_date == date(2026, 1, 9)
    assert event.ex_date == date(2026, 1, 12)
    assert event.payment_date == date(2026, 1, 30)
    assert event.dividend_type == expected_type
    assert float(event.value_per_unit) == pytest.approx(1.25)
    assert rights == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ticker,asset_type,_label,event_type",
    NATIONAL_DIVIDEND_CLASSES,
)
async def test_materialization_is_linked_and_idempotent_for_every_class(
    db: AsyncSession,
    portfolio: Portfolio,
    ticker: str,
    asset_type: str,
    _label: str,
    event_type: DividendType,
):
    asset = Asset(
        ticker=ticker,
        name=ticker,
        asset_type=asset_type,
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker=ticker,
            asset_type=asset_type,
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

    await materialize_asset_dividends(
        db,
        tickers=[ticker],
        portfolio_id=portfolio.id,
        commit=False,
    )
    await materialize_asset_dividends(
        db,
        tickers=[ticker],
        portfolio_id=portfolio.id,
        commit=False,
    )

    rights = (
        (
            await db.execute(
                select(Dividend).where(
                    Dividend.portfolio_id == portfolio.id,
                    Dividend.asset_dividend_id == event.id,
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(rights) == 1
    assert rights[0].ticker == ticker
    assert rights[0].dividend_type == event_type.value
    assert float(rights[0].quantity) == pytest.approx(10.0)
    assert float(rights[0].total_value) == pytest.approx(12.5)
    assert float(rights[0].net_value) == pytest.approx(12.5)
