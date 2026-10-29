"""Pure calculation of portfolio entitlements from global dividend events."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Iterable

logger = logging.getLogger(__name__)

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
    ex_date: date | None
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


def previous_business_day(d: date) -> date:
    """Return the closest business day strictly preceding ``d``."""
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5:  # 5: Saturday, 6: Sunday
        prev -= timedelta(days=1)
    return prev


def effective_entitlement_date(event: DividendEvent) -> date | None:
    """Resolve the economic cum-date (Data Com) for an event.

    If ``record_date`` is known, it is authoritative.
    If ``record_date`` is absent (e.g. providers that only report ex-date),
    the economic cum-date is derived as the business day immediately
    preceding ``ex_date`` only when ``payment_date`` is confirmed.
    Unconfirmed observations missing both ``record_date`` and ``payment_date``
    return ``None``.
    """
    if event.record_date is not None:
        return event.record_date
    if event.ex_date is not None and getattr(event, "payment_date", None) is not None:
        return previous_business_day(event.ex_date)
    return None


def historical_position(
    movements: Iterable[PositionMovement],
    reference_date: date,
) -> Decimal:
    """Return the position at end of ``reference_date`` without hiding oversells."""
    position = ZERO
    for movement in sorted(
        movements,
        key=lambda item: (
            item.transaction_date,
            0 if item.operation.lower().strip() == "buy" else 1,
        ),
    ):
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

    If ``record_date`` is missing, ``previous_business_day(ex_date)`` is used
    as the economic cum-date to protect against purchases on the ex-date.
    If neither date is present, the event is marked ambiguous.
    """
    event_type = event.event_type.upper().strip()
    currency = event.currency.upper().strip()
    if not currency:
        raise ValueError("event currency is required")
    value_per_unit = Decimal(event.value_per_unit)
    if value_per_unit < ZERO:
        raise ValueError("value per unit cannot be negative")

    entitlement_date = effective_entitlement_date(event)

    if event_type not in CASH_EVENT_TYPES:
        return _empty_entitlement(
            event, EntitlementReason.NON_CASH_EVENT, entitlement_date, currency
        )
    if entitlement_date is None:
        return _empty_entitlement(
            event,
            EntitlementReason.AMBIGUOUS_ENTITLEMENT_DATE,
            None,
            currency,
        )

    try:
        quantity = historical_position(movements, entitlement_date)
    except ValueError as exc:
        logger.warning(
            "historical_position failed for event_id=%s entitlement_date=%s: %s",
            event.event_id,
            entitlement_date,
            exc,
        )
        return _empty_entitlement(
            event, EntitlementReason.NO_POSITION, entitlement_date, currency
        )

    if quantity == ZERO:
        return _empty_entitlement(
            event, EntitlementReason.NO_POSITION, entitlement_date, currency
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
        entitlement_date=entitlement_date,
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
