from datetime import date
from decimal import Decimal

import pytest
from app.services.canonical_dividend_entitlement import (
    DividendEvent,
    EntitlementReason,
    PositionMovement,
    calculate_dividend_entitlement,
    historical_position,
)


def movement(day: int, operation: str, quantity: str) -> PositionMovement:
    return PositionMovement(date(2026, 1, day), operation, Decimal(quantity))


def event(
    *,
    record_date: date | None = date(2026, 1, 9),
    event_type: str = "DIVIDENDO",
    value: str = "1.25",
) -> DividendEvent:
    return DividendEvent(
        event_id=7,
        record_date=record_date,
        ex_date=date(2026, 1, 12),
        payment_date=date(2026, 1, 20),
        event_type=event_type,
        value_per_unit=Decimal(value),
        currency="brl",
    )


def test_calculates_entitlement_from_position_on_record_date() -> None:
    result = calculate_dividend_entitlement(
        event(),
        [movement(2, "buy", "10"), movement(8, "sell", "2")],
    )

    assert result.is_eligible
    assert result.eligible_quantity == Decimal("8")
    assert result.gross_amount == Decimal("10.00")
    assert result.net_amount == Decimal("10.00")
    assert result.currency == "BRL"


def test_sale_after_record_date_does_not_remove_historical_right() -> None:
    result = calculate_dividend_entitlement(
        event(),
        [movement(2, "buy", "10"), movement(10, "sell", "10")],
    )

    assert result.eligible_quantity == Decimal("10")


def test_repurchase_does_not_create_retroactive_right() -> None:
    result = calculate_dividend_entitlement(
        event(),
        [
            movement(2, "buy", "10"),
            movement(8, "sell", "10"),
            movement(13, "buy", "5"),
        ],
    )

    assert result.reason is EntitlementReason.NO_POSITION
    assert not result.is_eligible


def test_missing_record_date_is_ambiguous_instead_of_using_ex_date() -> None:
    result = calculate_dividend_entitlement(
        event(record_date=None),
        [movement(12, "buy", "10")],
    )

    assert result.reason is EntitlementReason.AMBIGUOUS_ENTITLEMENT_DATE
    assert result.entitlement_date is None
    assert result.eligible_quantity == Decimal("0")


@pytest.mark.parametrize("event_type", ["BONIFICACAO", "SUBSCRICAO", "OUTROS"])
def test_non_cash_or_unknown_event_does_not_enter_cash_totals(
    event_type: str,
) -> None:
    result = calculate_dividend_entitlement(
        event(event_type=event_type),
        [movement(2, "buy", "10")],
    )

    assert result.reason is EntitlementReason.NON_CASH_EVENT
    assert result.gross_amount == Decimal("0")


def test_jcp_exposes_gross_tax_and_net_amounts() -> None:
    result = calculate_dividend_entitlement(
        event(event_type="JCP", value="2"),
        [movement(2, "buy", "10")],
    )

    assert result.gross_amount == Decimal("20")
    assert result.withholding_tax == Decimal("3.00")
    assert result.net_amount == Decimal("17.00")


def test_invalid_history_is_not_silently_clamped_to_zero() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        historical_position([movement(2, "sell", "1")], date(2026, 1, 9))
