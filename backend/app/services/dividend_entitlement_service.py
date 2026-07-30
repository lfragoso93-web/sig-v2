"""Pure legacy-compatible calculations for dividend quantities and net values."""

from __future__ import annotations

from datetime import date

from app.models.dividend import DividendType
from app.models.transaction import OperationType


def calculate_net_quantity(txs: list[tuple], reference_date: date) -> float:
    """Calcula a posição líquida não negativa existente na data de referência."""
    quantity = 0.0
    for tx_date, operation, tx_quantity in txs:
        if tx_date > reference_date:
            continue
        operation_value = (
            operation.value
            if isinstance(operation, OperationType)
            else str(operation).lower()
        )
        if operation_value == OperationType.buy.value:
            quantity += float(tx_quantity)
        elif operation_value == OperationType.sell.value:
            quantity -= float(tx_quantity)
    return max(quantity, 0.0)


JCP_NET_FACTOR = 0.85


def calculate_net_value(dividend_type: DividendType, total_value: float) -> float:
    """Aplica a regra financeira canônica ao valor bruto do direito."""
    return (
        total_value * JCP_NET_FACTOR
        if dividend_type == DividendType.JCP
        else total_value
    )
