"""Pure calculation of portfolio entitlements from global dividend events."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Iterable


ZERO = Decimal("0")
JCP_NET_FACTOR = Decimal("0.85")
CASH_EVENT_TYPES = frozenset(
    {"DIVIDENDO", "JCP", "RENDIMENTO", "AMORTIZACAO"}
)


class EntitlementReason(str, Enum):
    ELIGIBLE = "eligible"
    NO_POSITION = "no_position"
    AMBIGUOUS_ENTITLEMENT_DATE = "ambiguous_entitlement_date"
    NON_CASH_EVENT = "non_cash_event"


@dataclass(frozen=True, slots=True)
class PositionMovement:
    transaction_date: date
    operation: str
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class DividendEvent:
    event_id: int
    record_date: date | None
    ex_date: date
    payment_date: date | None
    event_type: str
    value_per_unit: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class DividendEntitlement:
    event_id: int
    reason: EntitlementReason
    entitlement_date: date | None
    eligible_quantity: Decimal
    gross_amount: Decimal
    withholding_tax: Decimal
    net_amount: Decimal
    currency: str

    @property
    def is_eligible(self) -> bool:
        return self.reason is EntitlementReason.ELIGIBLE


def historical_position(
    movements: Iterable[PositionMovement],
    reference_date: date,
) -> Decimal:
    """Return the position at end of ``reference_date`` without hiding oversells."""
    position = ZERO
    for movement in sorted(movements, key=lambda item: item.transaction_date):
        if movement.transaction_date > reference_date:
            break
        quantity = Decimal(movement.quantity)
        if quantity <= ZERO:
            raise ValueError("movement quantity must be positive")
        operation = movement.operation.lower().strip()
        if operation == "buy":
            position += quantity
        elif operation == "sell":
            position -= quantity
        else:
            raise ValueError(f"unsupported movement operation: {movement.operation}")
        if position < ZERO:
            raise ValueError("historical position cannot be negative")
    return position


def calculate_dividend_entitlement(
    event: DividendEvent,
    movements: Iterable[PositionMovement],
) -> DividendEntitlement:
    """Calculate one entitlement without database access or side effects.

    ``record_date`` is the only accepted entitlement date. Falling back to
    ``ex_date`` could grant rights to a purchase made on the ex-date.
    """
    event_type = event.event_type.upper().strip()
    currency = event.currency.upper().strip()
    if not currency:
        raise ValueError("event currency is required")
    value_per_unit = Decimal(event.value_per_unit)
    if value_per_unit < ZERO:
        raise ValueError("value per unit cannot be negative")

    if event_type not in CASH_EVENT_TYPES:
        return _empty_entitlement(
            event, EntitlementReason.NON_CASH_EVENT, event.record_date, currency
        )
    if event.record_date is None:
        return _empty_entitlement(
            event,
            EntitlementReason.AMBIGUOUS_ENTITLEMENT_DATE,
            None,
            currency,
        )

    quantity = historical_position(movements, event.record_date)
    if quantity == ZERO:
        return _empty_entitlement(
            event, EntitlementReason.NO_POSITION, event.record_date, currency
        )

    gross_amount = quantity * value_per_unit
    net_amount = (
        gross_amount * JCP_NET_FACTOR
        if event_type == "JCP"
        else gross_amount
    )
    return DividendEntitlement(
        event_id=event.event_id,
        reason=EntitlementReason.ELIGIBLE,
        entitlement_date=event.record_date,
        eligible_quantity=quantity,
        gross_amount=gross_amount,
        withholding_tax=gross_amount - net_amount,
        net_amount=net_amount,
        currency=currency,
    )


def _empty_entitlement(
    event: DividendEvent,
    reason: EntitlementReason,
    entitlement_date: date | None,
    currency: str,
) -> DividendEntitlement:
    return DividendEntitlement(
        event_id=event.event_id,
        reason=reason,
        entitlement_date=entitlement_date,
        eligible_quantity=ZERO,
        gross_amount=ZERO,
        withholding_tax=ZERO,
        net_amount=ZERO,
        currency=currency,
    )
