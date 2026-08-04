"""Testes avançados do matcher quantitativo de Day Trade."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.irpf_day_trade_matcher import (
    FiscalOperation,
    FiscalTradeOperation,
    match_day_trades,
)


def _operation(
    transaction_id: int,
    operation: FiscalOperation,
    quantity: str,
    price: str,
    *,
    fees: str = "0",
) -> FiscalTradeOperation:
    return FiscalTradeOperation(
        transaction_id=transaction_id,
        ticker="BOVA11",
        trade_date=date(2024, 6, 3),
        operation=operation,
        quantity=Decimal(quantity),
        unit_price_brl=Decimal(price),
        fees_brl=Decimal(fees),
    )


def test_multiple_operations_use_fifo_and_preserve_remainders() -> None:
    result = match_day_trades(
        [
            _operation(1, FiscalOperation.BUY, "10", "10"),
            _operation(2, FiscalOperation.SELL, "4", "12"),
            _operation(3, FiscalOperation.BUY, "10", "14"),
            _operation(4, FiscalOperation.SELL, "16", "15"),
        ]
    )

    assert [match.quantity for match in result.matches] == [
        Decimal(4),
        Decimal(6),
        Decimal(10),
    ]
    assert [match.buy_transaction_id for match in result.matches] == [1, 1, 3]
    assert [match.sell_transaction_id for match in result.matches] == [2, 4, 4]
    assert result.unmatched_quantities == {
        1: Decimal(0),
        2: Decimal(0),
        3: Decimal(0),
        4: Decimal(0),
    }


def test_fees_are_allocated_proportionally_to_matched_quantity() -> None:
    result = match_day_trades(
        [
            _operation(1, FiscalOperation.BUY, "10", "10", fees="2"),
            _operation(2, FiscalOperation.SELL, "4", "15", fees="1"),
        ]
    )

    match = result.matches[0]
    assert match.allocated_buy_fees_brl == Decimal("0.8")
    assert match.allocated_sell_fees_brl == Decimal(1)
    assert match.gross_result_brl == Decimal("18.2")


@pytest.mark.parametrize(
    "operation",
    [
        FiscalTradeOperation(
            transaction_id=0,
            ticker="BOVA11",
            trade_date=date(2024, 6, 3),
            operation=FiscalOperation.BUY,
            quantity=Decimal(1),
            unit_price_brl=Decimal(10),
        ),
        FiscalTradeOperation(
            transaction_id=1,
            ticker="",
            trade_date=date(2024, 6, 3),
            operation=FiscalOperation.BUY,
            quantity=Decimal(1),
            unit_price_brl=Decimal(10),
        ),
        FiscalTradeOperation(
            transaction_id=1,
            ticker="BOVA11",
            trade_date=date(2024, 6, 3),
            operation=FiscalOperation.BUY,
            quantity=Decimal(0),
            unit_price_brl=Decimal(10),
        ),
        FiscalTradeOperation(
            transaction_id=1,
            ticker="BOVA11",
            trade_date=date(2024, 6, 3),
            operation=FiscalOperation.BUY,
            quantity=Decimal(1),
            unit_price_brl=Decimal(-1),
        ),
    ],
)
def test_invalid_operations_are_rejected(operation: FiscalTradeOperation) -> None:
    with pytest.raises(ValueError):
        match_day_trades([operation])
