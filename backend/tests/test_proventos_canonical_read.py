from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.models.dividend_enums import DividendStatus, DividendType
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


def entitlement(
    *,
    event_id: int = 1,
    event_type: str = "DIVIDENDO",
    record_date: date | None = None,
    payment_date: date | None = None,
    reason: EntitlementReason = EntitlementReason.ELIGIBLE,
    quantity: str = "10",
    gross: str = "12.50",
    net: str = "12.50",
    ticker: str = "ABCD3",
    asset_type: str = "ACAO",
) -> PortfolioDividendEntitlement:
    today = date.today()
    record_date = record_date or today - timedelta(days=30)
    payment_date = payment_date or today - timedelta(days=5)
    return PortfolioDividendEntitlement(
        ticker=ticker,
        asset_type=asset_type,
        event=DividendEvent(
            event_id=event_id,
            record_date=record_date,
            ex_date=today - timedelta(days=29),
            payment_date=payment_date,
            event_type=event_type,
            value_per_unit=Decimal("1.25"),
            currency="BRL",
        ),
        entitlement=DividendEntitlement(
            event_id=event_id,
            reason=reason,
            entitlement_date=record_date,
            eligible_quantity=Decimal(quantity),
            gross_amount=Decimal(gross),
            withholding_tax=Decimal(gross) - Decimal(net),
            net_amount=Decimal(net),
            currency="BRL",
        ),
        approved_on=None,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
    )


@pytest.fixture
def canonical_items(monkeypatch):
    items = [
        entitlement(),
        entitlement(
            event_id=2,
            event_type="JCP",
            payment_date=date.today() + timedelta(days=10),
            gross="10",
            net="8.50",
        ),
        entitlement(
            event_id=3,
            event_type="BONIFICACAO",
            reason=EntitlementReason.NON_CASH_EVENT,
            quantity="0",
            gross="0",
            net="0",
        ),
        entitlement(
            event_id=4,
            reason=EntitlementReason.AMBIGUOUS_ENTITLEMENT_DATE,
            record_date=None,
            quantity="0",
            gross="0",
            net="0",
        ),
    ]

    async def load(*_args, **_kwargs):
        return items

    monkeypatch.setattr(
        "app.services.proventos_service.load_portfolio_dividend_entitlements",
        load,
    )
    return items


@pytest.mark.asyncio
async def test_summary_uses_derived_rights_and_excludes_ambiguous_event(
    canonical_items,
):
    result = await get_summary(object(), 1)

    assert result["total_liquido_recebido"] == 12.5
    assert result["total_bruto_a_receber"] == 10.0
    assert result["total_liquido_a_receber"] == 8.5
    assert result["eventos_nao_cash"] == 1


@pytest.mark.asyncio
async def test_list_preserves_public_shape_without_legacy_dividend_rows(
    canonical_items,
):
    result = await list_items(object(), 1)

    assert result["total"] == 3
    assert {item["id"] for item in result["items"]} == {1, 2, 3}
    assert all("quantity" in item for item in result["items"])
    assert all(item["id"] != 4 for item in result["items"])


@pytest.mark.asyncio
async def test_filters_derive_status_from_payment_date(canonical_items):
    result = await list_items(
        object(),
        1,
        status=DividendStatus.A_RECEBER,
        dividend_type=DividendType.JCP,
    )

    assert [item["id"] for item in result["items"]] == [2]


@pytest.mark.asyncio
async def test_history_and_distribution_share_canonical_net_amounts(
    canonical_items,
):
    history = await get_monthly_history(object(), 1, status=DividendStatus.RECEBIDO)
    distribution = await get_distribution(object(), 1, status=DividendStatus.RECEBIDO)

    assert history[0]["total"] == 12.5
    assert distribution == [
        {
            "ticker": "ABCD3",
            "asset_type": "ACAO",
            "total": 12.5,
            "percentage": 100.0,
        }
    ]


def test_public_read_service_does_not_depend_on_legacy_dividend_model():
    from pathlib import Path

    source = (
        Path(__file__).parents[1] / "app" / "services" / "proventos_service.py"
    ).read_text(encoding="utf-8")

    assert "app.models.dividend import Dividend," not in source
    assert ".select_from(Dividend)" not in source
