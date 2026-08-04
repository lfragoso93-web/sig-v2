"""Testes do adaptador de transações para o matcher Day Trade."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.transaction import OperationType
from app.services.irpf_day_trade_matcher import FiscalOperation
from app.services.irpf_day_trade_transaction_adapter import (
    adapt_ordered_transactions,
    transaction_to_fiscal_trade_operation,
)


def _transaction(**overrides):
    values = {
        "id": 2,
        "ticker": "BOVA11",
        "date": date(2024, 5, 2),
        "operation": OperationType.buy,
        "quantity": 10.0,
        "price": 12.5,
        "price_brl": None,
        "fees": 1.25,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_adapter_prefers_persisted_brl_price() -> None:
    operation = transaction_to_fiscal_trade_operation(
        _transaction(price=10, price_brl=Decimal("51.25"))
    )

    assert operation.unit_price_brl == Decimal("51.25")
    assert operation.quantity == Decimal("10.0")
    assert operation.fees_brl == Decimal("1.25")
    assert operation.operation is FiscalOperation.BUY


def test_adapter_orders_by_date_and_transaction_id() -> None:
    result = adapt_ordered_transactions(
        [
            _transaction(id=3, date=date(2024, 5, 3)),
            _transaction(id=2, date=date(2024, 5, 2)),
            _transaction(id=1, date=date(2024, 5, 2)),
        ]
    )

    assert [item.transaction_id for item in result] == [1, 2, 3]


def test_adapter_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="operação fiscal inválida"):
        transaction_to_fiscal_trade_operation(_transaction(operation="bonus"))
