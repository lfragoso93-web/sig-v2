"""Adapta transações persistidas ao matcher quantitativo de Day Trade.

Este módulo não altera o runtime fiscal legado. Ele apenas normaliza e ordena
transações da carteira para o contrato puro ``FiscalTradeOperation``.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from app.models.transaction import OperationType
from app.services.irpf_day_trade_matcher import (
    FiscalOperation,
    FiscalTradeOperation,
)


def _decimal(value: object | None, *, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _operation_value(value: object) -> FiscalOperation:
    raw = value.value if isinstance(value, OperationType) else str(value)
    try:
        return FiscalOperation(raw)
    except ValueError as exc:
        raise ValueError(f"operação fiscal inválida: {raw}") from exc


def transaction_to_fiscal_trade_operation(transaction: object) -> FiscalTradeOperation:
    """Converte uma transação persistida para o contrato puro do matcher."""

    transaction_id = int(transaction.id)
    ticker = str(transaction.ticker)
    trade_date = transaction.date
    quantity = _decimal(transaction.quantity)
    fees_brl = _decimal(getattr(transaction, "fees", None))

    price_brl = getattr(transaction, "price_brl", None)
    unit_price_brl = (
        _decimal(price_brl)
        if price_brl is not None
        else _decimal(transaction.price)
    )

    return FiscalTradeOperation(
        transaction_id=transaction_id,
        ticker=ticker,
        trade_date=trade_date,
        operation=_operation_value(transaction.operation),
        quantity=quantity,
        unit_price_brl=unit_price_brl,
        fees_brl=fees_brl,
    )


def adapt_ordered_transactions(
    transactions: Iterable[object],
) -> tuple[FiscalTradeOperation, ...]:
    """Adapta e ordena por data e id para execução determinística."""

    operations = [
        transaction_to_fiscal_trade_operation(transaction)
        for transaction in transactions
    ]
    return tuple(
        sorted(
            operations,
            key=lambda item: (item.trade_date, item.transaction_id),
        )
    )
