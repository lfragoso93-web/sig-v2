from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.models.dividend_enums import DividendStatus
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    EntitlementReason,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
)
from app.services.proventos_service import (
    get_distribution,
    get_monthly_history,
    get_summary,
    list_items,
)


def canonical_item(
    *,
    event_id: int = 1,
    ticker: str = "VALE3",
    asset_type: str = "STOCK",
    event_type: str = "DIVIDENDO",
    payment_date: date | None = None,
    gross: str = "250",
    net: str = "250",
    quantity: str = "100",
    reason: EntitlementReason = EntitlementReason.ELIGIBLE,
) -> PortfolioDividendEntitlement:
    today = date.today()
    payment_date = payment_date or today - timedelta(days=5)
    event = DividendEvent(
        event_id=event_id,
        record_date=today - timedelta(days=30),
        ex_date=today - timedelta(days=29),
        payment_date=payment_date,
        event_type=event_type,
        value_per_unit=Decimal(gross) / Decimal(quantity),
        currency="BRL",
    )
    entitlement = DividendEntitlement(
        event_id=event_id,
        reason=reason,
        entitlement_date=event.record_date,
        eligible_quantity=Decimal(quantity),
        gross_amount=Decimal(gross),
        withholding_tax=Decimal(gross) - Decimal(net),
        net_amount=Decimal(net),
        currency="BRL",
    )
    return PortfolioDividendEntitlement(
        ticker=ticker,
        asset_type=asset_type,
        event=event,
        entitlement=entitlement,
        approved_on=None,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
    )


def install_items(monkeypatch, items):
    async def load(*_args, **_kwargs):
        return items

    monkeypatch.setattr(
        "app.services.proventos_service.load_portfolio_dividend_entitlements",
        load,
    )


@pytest.mark.asyncio
async def test_get_summary_no_dividends(monkeypatch):
    install_items(monkeypatch, [])

    result = await get_summary(object(), portfolio_id=1)

    assert result == {
        "total_recebido": 0.0,
        "total_liquido_recebido": 0.0,
        "total_bruto_recebido": 0.0,
        "total_a_receber": 0.0,
        "total_liquido_a_receber": 0.0,
        "total_bruto_a_receber": 0.0,
        "total_12m": 0.0,
        "media_mensal_12m": 0.0,
        "eventos_nao_cash": 0,
    }


@pytest.mark.asyncio
async def test_get_summary_with_dividends(monkeypatch):
    items = [
        canonical_item(event_id=1, gross="1600", net="1500"),
        canonical_item(
            event_id=2,
            payment_date=date.today() + timedelta(days=5),
            gross="550",
            net="500",
        ),
        canonical_item(
            event_id=3,
            event_type="BONIFICACAO",
            gross="0",
            net="0",
            reason=EntitlementReason.NON_CASH_EVENT,
        ),
        canonical_item(
            event_id=4,
            event_type="SUBSCRICAO",
            gross="0",
            net="0",
            reason=EntitlementReason.NON_CASH_EVENT,
        ),
    ]
    install_items(monkeypatch, items)

    result = await get_summary(object(), portfolio_id=1)

    assert result["total_recebido"] == 1500.0
    assert result["total_liquido_recebido"] == 1500.0
    assert result["total_bruto_recebido"] == 1600.0
    assert result["total_a_receber"] == 500.0
    assert result["total_liquido_a_receber"] == 500.0
    assert result["total_bruto_a_receber"] == 550.0
    assert result["total_12m"] == 1500.0
    assert result["media_mensal_12m"] == 125.0
    assert result["eventos_nao_cash"] == 2


@pytest.mark.asyncio
async def test_list_items_empty(monkeypatch):
    install_items(monkeypatch, [])

    result = await list_items(object(), portfolio_id=1)

    assert result["total"] == 0
    assert result["page"] == 1
    assert result["page_size"] == 50
    assert result["items"] == []


@pytest.mark.asyncio
async def test_list_items_with_data(monkeypatch):
    install_items(
        monkeypatch,
        [
            canonical_item(event_id=1),
            canonical_item(event_id=2, ticker="PETR4", gross="75", net="75"),
        ],
    )

    result = await list_items(object(), portfolio_id=1, page=1, page_size=1)

    assert result["total"] == 2
    assert len(result["items"]) == 1
    assert result["items"][0]["ticker"] == "PETR4"
    assert result["items"][0]["net_value"] == 75.0


@pytest.mark.asyncio
async def test_list_items_with_filters(monkeypatch):
    install_items(
        monkeypatch,
        [
            canonical_item(event_id=1),
            canonical_item(
                event_id=2,
                ticker="PETR4",
                payment_date=date.today() + timedelta(days=5),
                gross="75",
                net="75",
            ),
        ],
    )

    result = await list_items(
        object(),
        portfolio_id=1,
        status=DividendStatus.A_RECEBER,
        page=1,
        page_size=50,
    )

    assert result["total"] == 1
    assert result["items"][0]["ticker"] == "PETR4"
    assert result["items"][0]["status"] is DividendStatus.A_RECEBER


@pytest.mark.asyncio
async def test_get_monthly_history_empty(monkeypatch):
    install_items(monkeypatch, [])

    assert await get_monthly_history(object(), portfolio_id=1) == []


@pytest.mark.asyncio
async def test_get_monthly_history_with_data(monkeypatch):
    item = canonical_item(net="1500", gross="1500")
    install_items(monkeypatch, [item])

    result = await get_monthly_history(object(), portfolio_id=1)

    payment_date = item.event.payment_date
    assert payment_date is not None
    assert result[0]["year"] == payment_date.year
    assert result[0]["months"][payment_date.month - 1] == 1500.0
    assert result[0]["total"] == 1500.0
    assert result[0]["media"] == 1500.0


@pytest.mark.asyncio
async def test_get_monthly_history_multiple_years(monkeypatch):
    today = date.today()
    install_items(
        monkeypatch,
        [
            canonical_item(
                event_id=1,
                payment_date=date(today.year, 6, 15),
                gross="1000",
                net="1000",
            ),
            canonical_item(
                event_id=2,
                payment_date=date(today.year - 1, 12, 15),
                gross="500",
                net="500",
            ),
        ],
    )

    result = await get_monthly_history(object(), portfolio_id=1)

    assert [entry["year"] for entry in result] == [
        today.year,
        today.year - 1,
    ]


@pytest.mark.asyncio
async def test_get_distribution_empty(monkeypatch):
    install_items(monkeypatch, [])

    assert await get_distribution(object(), portfolio_id=1) == []


@pytest.mark.asyncio
async def test_get_distribution_single_asset(monkeypatch):
    install_items(
        monkeypatch,
        [canonical_item(gross="1000", net="1000")],
    )

    result = await get_distribution(object(), portfolio_id=1)

    assert result == [
        {
            "ticker": "VALE3",
            "asset_type": "STOCK",
            "total": 1000.0,
            "percentage": 100.0,
        }
    ]


@pytest.mark.asyncio
async def test_get_distribution_multiple_assets(monkeypatch):
    install_items(
        monkeypatch,
        [
            canonical_item(gross="1000", net="1000"),
            canonical_item(
                event_id=2,
                ticker="PETR4",
                gross="500",
                net="500",
            ),
        ],
    )

    result = await get_distribution(object(), portfolio_id=1)

    assert len(result) == 2
    assert result[0]["percentage"] == round(1000.0 / 1500.0 * 100, 2)
    assert result[1]["percentage"] == round(500.0 / 1500.0 * 100, 2)


@pytest.mark.asyncio
async def test_get_distribution_different_months(monkeypatch):
    install_items(
        monkeypatch,
        [
            canonical_item(
                payment_date=date.today() - timedelta(days=30),
                gross="1000",
                net="1000",
            )
        ],
    )

    result = await get_distribution(object(), portfolio_id=1, months=6)

    assert result[0]["total"] == 1000.0
