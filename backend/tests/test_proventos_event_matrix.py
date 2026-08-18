"""Matriz financeira dos tipos de evento do pipeline de Proventos."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.proventos_service import (
    get_distribution,
    get_monthly_history,
    get_summary,
    list_items,
)

@pytest.mark.asyncio
async def test_non_monetary_events_do_not_contaminate_financial_aggregates(
    db: AsyncSession,
    portfolio: Portfolio,
):
    today = date(2026, 7, 31)
    ticker = "EVN11"
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
            portfolio_id=portfolio.id,
            ticker=ticker,
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal(10),
            price=Decimal(100),
            date=today - timedelta(days=120),
        )
    )

    for offset, event_type in enumerate(
        (DividendType.BONIFICACAO, DividendType.SUBSCRICAO),
        start=1,
    ):
        event = AssetDividend(
            asset_id=asset.id,
            record_date=today - timedelta(days=30 - offset),
            ex_date=today - timedelta(days=29 - offset),
            payment_date=today - timedelta(days=5),
            value_per_unit=Decimal(0),
            dividend_type=event_type,
            source="canonical-test",
        )
        db.add(event)
        await db.flush()
    await db.flush()

    summary = await get_summary(db, portfolio.id)
    history = await get_monthly_history(db, portfolio.id)
    distribution = await get_distribution(db, portfolio.id)
    items = await list_items(db, portfolio.id)

    assert summary["total_liquido_recebido"] == 0.0
    assert summary["total_bruto_recebido"] == 0.0
    assert summary["total_12m"] == 0.0
    assert summary["eventos_nao_cash"] == 2
    assert history == []
    assert distribution == []
    assert items["total"] == 2
    assert {item["dividend_type"] for item in items["items"]} == {
        DividendType.BONIFICACAO,
        DividendType.SUBSCRICAO,
    }
    assert all(item["is_cash"] is False for item in items["items"])
