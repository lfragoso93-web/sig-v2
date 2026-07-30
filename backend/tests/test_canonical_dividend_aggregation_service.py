from datetime import date
from decimal import Decimal

from app.services.canonical_dividend_aggregation_service import (
    aggregate_received_entitlements,
    group_received_entitlements_by_day,
)
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    EntitlementReason,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
)


def _item(
    ticker: str,
    *,
    payment_date: date | None,
    net_amount: str,
    asset_type: str = "ACAO",
    reason: EntitlementReason = EntitlementReason.ELIGIBLE,
    currency: str = "BRL",
) -> PortfolioDividendEntitlement:
    event = DividendEvent(
        event_id=1,
        record_date=date(2026, 1, 2),
        ex_date=date(2026, 1, 3),
        payment_date=payment_date,
        event_type="DIVIDENDO",
        value_per_unit=Decimal("1"),
        currency=currency,
    )
    entitlement = DividendEntitlement(
        event_id=1,
        reason=reason,
        entitlement_date=event.record_date,
        eligible_quantity=Decimal("10"),
        gross_amount=Decimal(net_amount),
        withholding_tax=Decimal("0"),
        net_amount=Decimal(net_amount),
        currency=currency,
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


def test_aggregate_uses_payment_date_cutoff_and_as_of() -> None:
    items = [
        _item("PETR4", payment_date=date(2025, 12, 31), net_amount="10"),
        _item("PETR4", payment_date=date(2026, 1, 15), net_amount="20"),
        _item("PETR4", payment_date=date(2026, 3, 1), net_amount="30"),
    ]

    total = aggregate_received_entitlements(
        items,
        cutoff=date(2026, 1, 1),
        as_of=date(2026, 2, 1),
    )

    assert total == Decimal("20.00")


def test_aggregate_excludes_non_rights_unpaid_and_non_brl_events() -> None:
    items = [
        _item(
            "PETR4",
            payment_date=date(2026, 1, 15),
            net_amount="10",
            reason=EntitlementReason.NO_POSITION,
        ),
        _item("PETR4", payment_date=None, net_amount="20"),
        _item(
            "AAPL",
            payment_date=date(2026, 1, 15),
            net_amount="30",
            currency="USD",
        ),
    ]

    assert (
        aggregate_received_entitlements(items, as_of=date(2026, 2, 1))
        == Decimal("0.00")
    )


def test_aggregate_filters_tickers_without_mixing_assets() -> None:
    items = [
        _item("PETR4", payment_date=date(2026, 1, 15), net_amount="10.125"),
        _item("VALE3", payment_date=date(2026, 1, 15), net_amount="20"),
    ]

    total = aggregate_received_entitlements(
        items,
        as_of=date(2026, 2, 1),
        tickers=("petr4",),
    )

    assert total == Decimal("10.13")


def test_snapshot_projection_moves_weekend_payment_and_accumulates() -> None:
    items = [
        _item("PETR4", payment_date=date(2026, 7, 18), net_amount="10.125"),
        _item("VALE3", payment_date=date(2026, 7, 20), net_amount="20"),
        _item(
            "AAPL",
            payment_date=date(2026, 7, 20),
            net_amount="30",
            currency="USD",
        ),
    ]

    by_day, accumulated = group_received_entitlements_by_day(items)

    assert by_day == {date(2026, 7, 20): Decimal("30.13")}
    assert accumulated == {date(2026, 7, 20): Decimal("30.13")}


def test_snapshot_projection_filters_asset_type() -> None:
    stock = _item("PETR4", payment_date=date(2026, 7, 20), net_amount="10")
    fii = _item(
        "FUND11",
        payment_date=date(2026, 7, 20),
        net_amount="5",
        asset_type="FII",
    )

    by_day, _ = group_received_entitlements_by_day(
        [stock, fii],
        asset_types=("FII",),
    )

    assert by_day == {date(2026, 7, 20): Decimal("5.00")}
