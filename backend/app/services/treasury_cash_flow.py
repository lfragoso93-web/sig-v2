"""Pure Treasury cash-flow and source-withholding contracts.

This module deliberately does not read a provider or persist a portfolio cash
balance.  A Treasury event is a global gross fact; the taxable amount and IRRF
are projected per acquisition lot because their holding periods can differ.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


_ZERO = Decimal("0")
_MONEY = Decimal("0.01")


def conservative_treasury_custody_date(
    transaction_date: date,
    *,
    is_business_day: Callable[[date], bool],
) -> date:
    """Return the SGI's disclosed conservative D+2-business-day custody date."""
    cursor = transaction_date
    found = 0
    while found < 2:
        cursor = date.fromordinal(cursor.toordinal() + 1)
        if is_business_day(cursor):
            found += 1
    return cursor


@dataclass(frozen=True, slots=True)
class TreasuryCashEvent:
    """A persisted global cash event, expressed in gross BRL per unit.

    ``taxable_income_per_unit`` is intentionally explicit.  A periodic coupon
    acquired between coupon dates can have a different taxable component per
    lot; deriving it from a price or from an annual rate would be fictitious.
    """

    event_id: int
    event_type: str
    record_date: date
    payment_date: date
    gross_value_per_unit: Decimal
    taxable_income_per_unit: Decimal
    currency: str = "BRL"


@dataclass(frozen=True, slots=True)
class TreasuryAcquisitionLot:
    """One eligible Treasury acquisition with its fiscal start date."""

    lot_id: int
    acquisition_date: date
    eligible_quantity: Decimal


@dataclass(frozen=True, slots=True)
class TreasuryLotCashFlow:
    """Read-only portfolio projection for one event and one acquisition lot."""

    event_id: int
    lot_id: int
    payment_date: date
    gross_amount: Decimal
    taxable_income: Decimal
    withholding_rate: Decimal
    withholding_tax: Decimal
    net_amount: Decimal
    currency: str


def treasury_withholding_rate(acquisition_date: date, payment_date: date) -> Decimal:
    """Return the statutory regressive IRRF rate for an explicit holding period."""

    holding_days = (payment_date - acquisition_date).days
    if holding_days < 0:
        raise ValueError("treasury acquisition date cannot be after payment date")
    if holding_days <= 180:
        return Decimal("0.225")
    if holding_days <= 360:
        return Decimal("0.20")
    if holding_days <= 720:
        return Decimal("0.175")
    return Decimal("0.15")


def calculate_treasury_lot_cash_flow(
    event: TreasuryCashEvent,
    lot: TreasuryAcquisitionLot,
) -> TreasuryLotCashFlow:
    """Project gross, IRRF and net cash without materializing a new ledger fact."""

    currency = event.currency.strip().upper()
    event_type = event.event_type.strip().upper()
    quantity = Decimal(lot.eligible_quantity)
    gross_per_unit = Decimal(event.gross_value_per_unit)
    taxable_per_unit = Decimal(event.taxable_income_per_unit)

    if event_type not in {"RENDIMENTO", "AMORTIZACAO"}:
        raise ValueError(f"unsupported treasury cash event type: {event.event_type}")
    if not currency:
        raise ValueError("treasury cash event currency is required")
    if event.record_date > event.payment_date:
        raise ValueError("treasury record date cannot be after payment date")
    if lot.acquisition_date > event.record_date:
        raise ValueError("treasury lot is not eligible on record date")
    if quantity <= _ZERO:
        raise ValueError("treasury eligible quantity must be positive")
    if gross_per_unit < _ZERO or taxable_per_unit < _ZERO:
        raise ValueError("treasury per-unit values cannot be negative")
    if taxable_per_unit > gross_per_unit:
        raise ValueError("treasury taxable income cannot exceed gross cash")

    gross_amount = (quantity * gross_per_unit).quantize(_MONEY, rounding=ROUND_HALF_UP)
    taxable_income = (quantity * taxable_per_unit).quantize(
        _MONEY, rounding=ROUND_HALF_UP
    )
    rate = treasury_withholding_rate(lot.acquisition_date, event.payment_date)
    withholding_tax = (taxable_income * rate).quantize(_MONEY, rounding=ROUND_HALF_UP)
    return TreasuryLotCashFlow(
        event_id=event.event_id,
        lot_id=lot.lot_id,
        payment_date=event.payment_date,
        gross_amount=gross_amount,
        taxable_income=taxable_income,
        withholding_rate=rate,
        withholding_tax=withholding_tax,
        net_amount=gross_amount - withholding_tax,
        currency=currency,
    )
