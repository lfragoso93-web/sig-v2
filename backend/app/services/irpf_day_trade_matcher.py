"""Matching quantitativo e determinístico de operações Day Trade.

Este módulo é puro e não altera o runtime fiscal legado. Ele separa, por
carteira implícita, data e ticker, apenas a quantidade efetivamente comprada e
vendida no mesmo pregão. O excedente permanece disponível para Swing Trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Iterable


class FiscalOperation(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class FiscalTradeOperation:
    transaction_id: int
    ticker: str
    trade_date: date
    operation: FiscalOperation
    quantity: Decimal
    unit_price_brl: Decimal
    fees_brl: Decimal = Decimal(0)


@dataclass(frozen=True)
class DayTradeMatch:
    ticker: str
    trade_date: date
    buy_transaction_id: int
    sell_transaction_id: int
    quantity: Decimal
    buy_unit_price_brl: Decimal
    sell_unit_price_brl: Decimal
    allocated_buy_fees_brl: Decimal
    allocated_sell_fees_brl: Decimal

    @property
    def gross_result_brl(self) -> Decimal:
        return (
            (self.sell_unit_price_brl - self.buy_unit_price_brl) * self.quantity
            - self.allocated_buy_fees_brl
            - self.allocated_sell_fees_brl
        )


@dataclass(frozen=True)
class DayTradeMatchingResult:
    matches: tuple[DayTradeMatch, ...]
    unmatched_quantities: dict[int, Decimal]


def _validate_operation(operation: FiscalTradeOperation) -> None:
    if operation.transaction_id <= 0:
        raise ValueError("transaction_id deve ser positivo")
    if not operation.ticker.strip():
        raise ValueError("ticker é obrigatório")
    if operation.quantity <= 0:
        raise ValueError("quantity deve ser positiva")
    if operation.unit_price_brl < 0:
        raise ValueError("unit_price_brl não pode ser negativo")
    if operation.fees_brl < 0:
        raise ValueError("fees_brl não pode ser negativo")


def _allocate_fees(
    *,
    total_fees: Decimal,
    matched_quantity: Decimal,
    original_quantity: Decimal,
) -> Decimal:
    if total_fees == 0:
        return Decimal(0)
    return total_fees * matched_quantity / original_quantity


def match_day_trades(
    operations: Iterable[FiscalTradeOperation],
) -> DayTradeMatchingResult:
    """Casa compras e vendas pela ordem informada, isolando data e ticker.

    A ordem de entrada deve refletir a ordenação canônica das transações. O
    algoritmo usa filas FIFO independentes para compras e vendas, permitindo
    múltiplas operações intercaladas e mantendo o excedente como não casado.
    """

    ordered = tuple(operations)
    for operation in ordered:
        _validate_operation(operation)

    unmatched = {operation.transaction_id: operation.quantity for operation in ordered}
    matches: list[DayTradeMatch] = []

    grouped: dict[tuple[date, str], list[FiscalTradeOperation]] = {}
    for operation in ordered:
        key = (operation.trade_date, operation.ticker.strip().upper())
        grouped.setdefault(key, []).append(operation)

    for (trade_date, ticker), group in grouped.items():
        buys: list[FiscalTradeOperation] = []
        sells: list[FiscalTradeOperation] = []

        for operation in group:
            if operation.operation is FiscalOperation.BUY:
                buys.append(operation)
            else:
                sells.append(operation)

        buy_index = 0
        sell_index = 0
        while buy_index < len(buys) and sell_index < len(sells):
            buy = buys[buy_index]
            sell = sells[sell_index]
            quantity = min(
                unmatched[buy.transaction_id],
                unmatched[sell.transaction_id],
            )
            if quantity <= 0:
                if unmatched[buy.transaction_id] <= 0:
                    buy_index += 1
                if unmatched[sell.transaction_id] <= 0:
                    sell_index += 1
                continue

            matches.append(
                DayTradeMatch(
                    ticker=ticker,
                    trade_date=trade_date,
                    buy_transaction_id=buy.transaction_id,
                    sell_transaction_id=sell.transaction_id,
                    quantity=quantity,
                    buy_unit_price_brl=buy.unit_price_brl,
                    sell_unit_price_brl=sell.unit_price_brl,
                    allocated_buy_fees_brl=_allocate_fees(
                        total_fees=buy.fees_brl,
                        matched_quantity=quantity,
                        original_quantity=buy.quantity,
                    ),
                    allocated_sell_fees_brl=_allocate_fees(
                        total_fees=sell.fees_brl,
                        matched_quantity=quantity,
                        original_quantity=sell.quantity,
                    ),
                )
            )
            unmatched[buy.transaction_id] -= quantity
            unmatched[sell.transaction_id] -= quantity

            if unmatched[buy.transaction_id] == 0:
                buy_index += 1
            if unmatched[sell.transaction_id] == 0:
                sell_index += 1

    return DayTradeMatchingResult(
        matches=tuple(matches),
        unmatched_quantities=unmatched,
    )
