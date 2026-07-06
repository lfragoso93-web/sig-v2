from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.proventos_service import get_distribution, get_monthly_history, get_summary, list_items


async def make_asset(db: AsyncSession, ticker: str, asset_type: str = "ACAO") -> Asset:
    asset = Asset(ticker=ticker, name=ticker, asset_type=asset_type, currency="BRL")
    db.add(asset)
    await db.flush()
    return asset


async def make_tx(db: AsyncSession, portfolio_id: int, ticker: str, tx_date: date) -> None:
    db.add(Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        operation=OperationType.buy,
        quantity=100,
        date=tx_date,
        price=Decimal("10.00"),
        asset_type="ACAO",
    ))
    await db.flush()


async def make_event(
    db: AsyncSession,
    asset: Asset,
    record_date: date | None,
    ex_date: date,
    payment_date: date | None,
    dividend_type: DividendType,
    value_per_unit: str = "1.00",
) -> AssetDividend:
    event = AssetDividend(
        asset_id=asset.id,
        record_date=record_date,
        ex_date=ex_date,
        payment_date=payment_date,
        value_per_unit=Decimal(value_per_unit),
        dividend_type=dividend_type,
        source="test",
    )
    db.add(event)
    await db.flush()
    return event


async def make_dividend(
    db: AsyncSession,
    portfolio_id: int,
    event: AssetDividend,
    total: str,
    net: str,
    status: DividendStatus = DividendStatus.RECEBIDO,
) -> None:
    db.add(Dividend(
        portfolio_id=portfolio_id,
        asset_dividend_id=event.id,
        quantity=Decimal("100"),
        total_value=Decimal(total),
        net_value=Decimal(net),
        status=status,
    ))
    await db.flush()


@pytest.mark.asyncio
async def test_issue95_summary_cash_vs_non_cash(db: AsyncSession, portfolio: Portfolio):
    asset = await make_asset(db, "PETR4")
    await make_tx(db, portfolio.id, "PETR4", date(2024, 1, 1))

    cash = await make_event(db, asset, date(2024, 3, 1), date(2024, 3, 4), date.today(), DividendType.JCP)
    await make_dividend(db, portfolio.id, cash, "100.00", "85.00")

    future = await make_event(db, asset, date(2024, 4, 1), date(2024, 4, 2), date.today(), DividendType.DIVIDENDO)
    await make_dividend(db, portfolio.id, future, "50.00", "50.00", DividendStatus.A_RECEBER)

    non_cash = await make_event(db, asset, date(2024, 5, 1), date(2024, 5, 2), date.today(), DividendType.BONIFICACAO, "0.00")
    await make_dividend(db, portfolio.id, non_cash, "999.00", "999.00")

    summary = await get_summary(db, portfolio.id)

    assert summary["total_liquido_recebido"] == pytest.approx(85.0)
    assert summary["total_bruto_recebido"] == pytest.approx(100.0)
    assert summary["total_liquido_a_receber"] == pytest.approx(50.0)
    assert summary["eventos_nao_cash"] == 1


@pytest.mark.asyncio
async def test_issue95_list_uses_record_date_before_ex_date(db: AsyncSession, portfolio: Portfolio):
    asset = await make_asset(db, "BBAS3")
    await make_tx(db, portfolio.id, "BBAS3", date(2024, 1, 3))

    no_rights = await make_event(db, asset, date(2024, 1, 1), date(2024, 1, 4), date(2024, 1, 20), DividendType.DIVIDENDO)
    await make_dividend(db, portfolio.id, no_rights, "100.00", "100.00")

    fallback = await make_event(db, asset, None, date(2024, 1, 4), date(2024, 1, 25), DividendType.DIVIDENDO)
    await make_dividend(db, portfolio.id, fallback, "100.00", "100.00")

    result = await list_items(db, portfolio.id)

    assert result["total"] == 1
    assert result["items"][0]["payment_date"] == date(2024, 1, 25)


@pytest.mark.asyncio
async def test_issue95_history_and_distribution_ignore_non_cash(db: AsyncSession, portfolio: Portfolio):
    asset = await make_asset(db, "MXRF11", "FII")
    await make_tx(db, portfolio.id, "MXRF11", date(2024, 1, 1))

    cash = await make_event(db, asset, date(2024, 6, 1), date(2024, 6, 3), date.today(), DividendType.RENDIMENTO)
    await make_dividend(db, portfolio.id, cash, "120.00", "120.00")

    non_cash = await make_event(db, asset, date(2024, 6, 5), date(2024, 6, 6), date.today(), DividendType.SUBSCRICAO, "0.00")
    await make_dividend(db, portfolio.id, non_cash, "500.00", "500.00")

    history = await get_monthly_history(db, portfolio.id)
    distribution = await get_distribution(db, portfolio.id, months=24)

    assert history[0]["total"] == pytest.approx(120.0)
    assert distribution[0]["ticker"] == "MXRF11"
    assert distribution[0]["total"] == pytest.approx(120.0)
    assert distribution[0]["percentage"] == pytest.approx(100.0)
