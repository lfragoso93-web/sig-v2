"""Matriz ponta a ponta das classes nacionais com Proventos."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendType
from app.services.dividend_backfill_service import backfill_dividends


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
        await backfill_dividends(db, None, ticker, asset_type)

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
