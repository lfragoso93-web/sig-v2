from datetime import date
from decimal import Decimal

import pytest

from app.services.treasury_cash_flow import (
    TreasuryAcquisitionLot,
    TreasuryCashEvent,
    calculate_treasury_lot_cash_flow,
    treasury_withholding_rate,
)


def _event(*, taxable_per_unit: str = "48.81") -> TreasuryCashEvent:
    return TreasuryCashEvent(
        event_id=91,
        event_type="RENDIMENTO",
        record_date=date(2026, 7, 1),
        payment_date=date(2026, 7, 1),
        gross_value_per_unit=Decimal("48.81"),
        taxable_income_per_unit=Decimal(taxable_per_unit),
        currency="brl",
    )


def _lot(*, acquired: date = date(2025, 1, 1), quantity: str = "2") -> TreasuryAcquisitionLot:
    return TreasuryAcquisitionLot(
        lot_id=31,
        acquisition_date=acquired,
        eligible_quantity=Decimal(quantity),
    )


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (180, "0.225"),
        (181, "0.20"),
        (360, "0.20"),
        (361, "0.175"),
        (720, "0.175"),
        (721, "0.15"),
    ],
)
def test_treasury_withholding_rate_respects_regressive_boundaries(
    days: int,
    expected: str,
) -> None:
    acquired = date(2024, 1, 1)
    assert treasury_withholding_rate(acquired, date.fromordinal(acquired.toordinal() + days)) == Decimal(expected)


def test_treasury_cash_flow_keeps_gross_irrf_and_net_separate_per_lot() -> None:
    result = calculate_treasury_lot_cash_flow(_event(), _lot())

    assert result.gross_amount == Decimal("97.62")
    assert result.taxable_income == Decimal("97.62")
    assert result.withholding_rate == Decimal("0.175")
    assert result.withholding_tax == Decimal("17.08")
    assert result.net_amount == Decimal("80.54")
    assert result.currency == "BRL"


def test_treasury_cash_flow_accepts_explicit_partial_taxable_component() -> None:
    result = calculate_treasury_lot_cash_flow(_event(taxable_per_unit="20"), _lot())

    assert result.gross_amount == Decimal("97.62")
    assert result.taxable_income == Decimal("40.00")
    assert result.withholding_tax == Decimal("7.00")
    assert result.net_amount == Decimal("90.62")


def test_treasury_cash_flow_rejects_lot_without_event_day_eligibility() -> None:
    with pytest.raises(ValueError, match="not eligible"):
        calculate_treasury_lot_cash_flow(
            _event(),
            _lot(acquired=date(2026, 7, 2)),
        )


def test_treasury_cash_flow_rejects_invented_taxable_income() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        calculate_treasury_lot_cash_flow(_event(taxable_per_unit="50"), _lot())
