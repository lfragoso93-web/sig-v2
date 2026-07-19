from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.schemas.proventos import (
    ProventosDistributionResponse,
    ProventosListResponse,
    ProventosMonthlyHistoryResponse,
    ProventosSummaryResponse,
)
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

    fallback = await make_event(db, asset, None, date(2024, 1, 5), date(2024, 1, 25), DividendType.DIVIDENDO)
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


@pytest.mark.asyncio
async def test_issue131_monthly_history_breaks_total_down_by_asset_class(
    db: AsyncSession,
    portfolio: Portfolio,
):
    payment_date = date(2026, 3, 20)
    assets = [
        await make_asset(db, "PETR4", "ACAO"),
        await make_asset(db, "MXRF11", "FII"),
        await make_asset(db, "BOVA11", "ETF_NACIONAL"),
    ]
    values = ["23.645", "90.80", "37.00"]

    for asset, value in zip(assets, values):
        await make_tx(db, portfolio.id, asset.ticker, date(2025, 1, 1))
        event = await make_event(
            db,
            asset,
            date(2026, 3, 1),
            date(2026, 3, 2),
            payment_date,
            DividendType.RENDIMENTO if asset.asset_type == "FII" else DividendType.DIVIDENDO,
        )
        await make_dividend(db, portfolio.id, event, value, value)

    history = await get_monthly_history(db, portfolio.id)

    march = history[0]["month_details"][0]
    assert march["month"] == 3
    assert march["by_asset_class"] == [
        {"asset_type": "FII", "label": "FIIs", "value": 90.8},
        {"asset_type": "ETF_NACIONAL", "label": "ETFs nacionais", "value": 37.0},
        {"asset_type": "ACAO", "label": "Ações", "value": 23.65},
    ]
    assert march["total"] == pytest.approx(151.45)
    assert history[0]["months"][2] == pytest.approx(march["total"])
    assert sum(item["value"] for item in march["by_asset_class"]) == pytest.approx(march["total"])


@pytest.mark.asyncio
async def test_issue131_monthly_breakdown_respects_filters_and_portfolio_isolation(
    db: AsyncSession,
    portfolio: Portfolio,
):
    other_portfolio = Portfolio(
        user_id=portfolio.user_id,
        name="Outra carteira",
        description="",
    )
    db.add(other_portfolio)
    await db.flush()

    asset = await make_asset(db, "HGLG11", "FII")
    event = await make_event(
        db,
        asset,
        date(2026, 4, 1),
        date(2026, 4, 2),
        date(2026, 4, 20),
        DividendType.RENDIMENTO,
    )
    for target, value in ((portfolio, "60.00"), (other_portfolio, "900.00")):
        await make_tx(db, target.id, asset.ticker, date(2025, 1, 1))
        await make_dividend(db, target.id, event, value, value)

    non_cash = await make_event(
        db,
        asset,
        date(2026, 4, 3),
        date(2026, 4, 4),
        date(2026, 4, 20),
        DividendType.BONIFICACAO,
    )
    await make_dividend(db, portfolio.id, non_cash, "500.00", "500.00")

    history = await get_monthly_history(
        db,
        portfolio.id,
        status=DividendStatus.RECEBIDO,
        year=2026,
        asset_type="FII",
        dividend_type=DividendType.RENDIMENTO,
    )

    assert history[0]["total"] == pytest.approx(60.0)
    assert history[0]["month_details"] == [{
        "month": 4,
        "total": 60.0,
        "by_asset_class": [{"asset_type": "FII", "label": "FIIs", "value": 60.0}],
    }]



@pytest.mark.asyncio
async def test_issue165_filters_keep_aggregates_in_the_same_cash_universe(
    db: AsyncSession,
    portfolio: Portfolio,
):
    today = date.today()
    bought_on = today - timedelta(days=120)
    record_date = today - timedelta(days=30)
    ex_date = today - timedelta(days=29)
    payment_date = today - timedelta(days=5)

    stock = await make_asset(db, "VALE3")
    fii = await make_asset(db, "HGLG11", "FII")
    await make_tx(db, portfolio.id, stock.ticker, bought_on)
    await make_tx(db, portfolio.id, fii.ticker, bought_on)

    stock_event = await make_event(
        db,
        stock,
        record_date,
        ex_date,
        payment_date,
        DividendType.DIVIDENDO,
    )
    fii_event = await make_event(
        db,
        fii,
        record_date,
        ex_date,
        payment_date,
        DividendType.RENDIMENTO,
    )
    await make_dividend(db, portfolio.id, stock_event, "100.00", "100.00")
    await make_dividend(db, portfolio.id, fii_event, "60.00", "60.00")

    filters = {
        "asset_type": "FII",
        "dividend_type": DividendType.RENDIMENTO,
    }
    summary = await get_summary(db, portfolio.id, **filters)
    items = await list_items(db, portfolio.id, **filters)
    history = await get_monthly_history(db, portfolio.id, **filters)

    assert summary["total_liquido_recebido"] == pytest.approx(60.0)
    assert items["total"] == 1
    assert items["items"][0]["ticker"] == "HGLG11"
    assert sum(row["total"] for row in history) == pytest.approx(60.0)


@pytest.mark.asyncio
async def test_issue165_year_is_recognized_by_payment_date(
    db: AsyncSession,
    portfolio: Portfolio,
):
    current_year = date.today().year
    asset = await make_asset(db, "TAEE11")
    await make_tx(db, portfolio.id, asset.ticker, date(current_year - 2, 1, 2))

    event = await make_event(
        db,
        asset,
        date(current_year - 1, 12, 15),
        date(current_year - 1, 12, 16),
        date(current_year, 1, 15),
        DividendType.DIVIDENDO,
    )
    await make_dividend(db, portfolio.id, event, "75.00", "75.00")

    current_summary = await get_summary(db, portfolio.id, year=current_year)
    previous_summary = await get_summary(db, portfolio.id, year=current_year - 1)
    current_items = await list_items(db, portfolio.id, year=current_year)
    previous_items = await list_items(db, portfolio.id, year=current_year - 1)
    history = await get_monthly_history(db, portfolio.id, year=current_year)

    assert current_summary["total_liquido_recebido"] == pytest.approx(75.0)
    assert previous_summary["total_liquido_recebido"] == pytest.approx(0.0)
    assert current_items["total"] == 1
    assert previous_items["total"] == 0
    assert history[0]["year"] == current_year
    assert history[0]["months"][0] == pytest.approx(75.0)


@pytest.mark.asyncio
async def test_issue165_distribution_uses_the_same_filters_as_summary(
    db: AsyncSession,
    portfolio: Portfolio,
):
    today = date.today()
    bought_on = today - timedelta(days=120)
    record_date = today - timedelta(days=30)
    ex_date = today - timedelta(days=29)
    payment_date = today - timedelta(days=5)

    stock = await make_asset(db, "WEGE3")
    fii = await make_asset(db, "KNRI11", "FII")
    await make_tx(db, portfolio.id, stock.ticker, bought_on)
    await make_tx(db, portfolio.id, fii.ticker, bought_on)

    stock_event = await make_event(
        db,
        stock,
        record_date,
        ex_date,
        payment_date,
        DividendType.DIVIDENDO,
    )
    fii_event = await make_event(
        db,
        fii,
        record_date,
        ex_date,
        payment_date,
        DividendType.RENDIMENTO,
    )
    await make_dividend(db, portfolio.id, stock_event, "40.00", "40.00")
    await make_dividend(db, portfolio.id, fii_event, "60.00", "60.00")

    filtered_summary = await get_summary(db, portfolio.id, asset_type="FII")
    distribution = await get_distribution(
        db,
        portfolio.id,
        months=12,
        asset_type="FII",
    )

    assert filtered_summary["total_liquido_recebido"] == pytest.approx(60.0)
    assert {row["ticker"] for row in distribution} == {"KNRI11"}
    assert sum(row["total"] for row in distribution) == pytest.approx(60.0)



@pytest.mark.asyncio
async def test_issue165_strict_response_contracts_validate_service_payloads(
    db: AsyncSession,
    portfolio: Portfolio,
):
    today = date.today()
    asset = await make_asset(db, "BBDC4")
    await make_tx(db, portfolio.id, asset.ticker, today - timedelta(days=120))

    event = await make_event(
        db,
        asset,
        today - timedelta(days=30),
        today - timedelta(days=29),
        today - timedelta(days=5),
        DividendType.DIVIDENDO,
    )
    await make_dividend(db, portfolio.id, event, "90.00", "90.00")

    summary = await get_summary(db, portfolio.id)
    items = await list_items(db, portfolio.id)
    history = await get_monthly_history(db, portfolio.id)
    distribution = await get_distribution(db, portfolio.id)

    ProventosSummaryResponse.model_validate(summary)
    ProventosListResponse.model_validate(items)
    ProventosMonthlyHistoryResponse.model_validate(history[0])
    ProventosDistributionResponse.model_validate(distribution[0])

    with pytest.raises(ValidationError):
        ProventosSummaryResponse.model_validate({
            **summary,
            "campo_inesperado": True,
        })



@pytest.mark.asyncio
async def test_issue165_read_services_do_not_mutate_session(
    db: AsyncSession,
    portfolio: Portfolio,
    monkeypatch: pytest.MonkeyPatch,
):
    today = date.today()
    asset = await make_asset(db, "SANB11")
    await make_tx(db, portfolio.id, asset.ticker, today - timedelta(days=120))
    event = await make_event(
        db,
        asset,
        today - timedelta(days=30),
        today - timedelta(days=29),
        today - timedelta(days=5),
        DividendType.DIVIDENDO,
    )
    await make_dividend(db, portfolio.id, event, "50.00", "50.00")
    await db.flush()

    commit_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)

    await get_summary(db, portfolio.id)
    await list_items(db, portfolio.id)
    await get_monthly_history(db, portfolio.id)
    await get_distribution(db, portfolio.id)

    commit_mock.assert_not_awaited()
    assert list(db.new) == []
    assert list(db.dirty) == []
    assert list(db.deleted) == []
