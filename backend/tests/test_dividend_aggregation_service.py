from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.dividend_aggregation_service import (
    aggregate_received_dividends,
    is_received_cash_dividend,
    received_dividend_value,
)


def _dividend(**overrides):
    data = {
        "status": "RECEBIDO",
        "dividend_type": "DIVIDENDO",
        "payment_date": date(2026, 7, 10),
        "date_pagamento": None,
        "net_value": Decimal("85.00"),
        "total_received": Decimal("100.00"),
        "total_value": Decimal("100.00"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_received_value_prefers_net_amount() -> None:
    assert received_dividend_value(_dividend()) == Decimal("85.00")


def test_pending_dividend_is_not_received_cash() -> None:
    assert is_received_cash_dividend(_dividend(status="A_RECEBER")) is False


def test_non_cash_event_is_excluded() -> None:
    assert is_received_cash_dividend(_dividend(dividend_type="BONIFICACAO")) is False


def test_aggregation_uses_payment_date_and_cutoff() -> None:
    dividends = [
        _dividend(payment_date=date(2025, 7, 9), net_value=Decimal("10")),
        _dividend(payment_date=date(2025, 7, 10), net_value=Decimal("20")),
        _dividend(payment_date=date(2026, 7, 10), net_value=Decimal("30")),
        _dividend(payment_date=date(2026, 7, 11), net_value=Decimal("40"), status="A_RECEBER"),
    ]

    total = aggregate_received_dividends(
        dividends,
        cutoff=date(2025, 7, 10),
        as_of=date(2026, 7, 10),
    )

    assert total == Decimal("50.00")


def test_legacy_payment_date_is_supported() -> None:
    dividend = _dividend(payment_date=None, date_pagamento=date(2026, 7, 10))
    assert aggregate_received_dividends([dividend]) == Decimal("85.00")
