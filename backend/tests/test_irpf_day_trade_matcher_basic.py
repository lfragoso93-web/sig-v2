"""Testes básicos do matcher quantitativo de Day Trade."""

from datetime import date
from decimal import Decimal

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
    ticker: str = "BOVA11",
    trade_date: date = date(2024, 5, 2),
    fees: str = "0",
) -> FiscalTradeOperation:
    return FiscalTradeOperation(
        transaction_id=transaction_id,
        ticker=ticker,
        trade_date=trade_date,
        operation=operation,
        quantity=Decimal(quantity),
        unit_price_brl=Decimal(price),
        fees_brl=Decimal(fees),
    )


def test_partial_intraday_match_keeps_remainder_unmatched() -> None:
    result = match_day_trades(
        [
            _operation(1, FiscalOperation.BUY, "20", "10"),
            _operation(2, FiscalOperation.SELL, "5", "12"),
        ]
    )

    assert len(result.matches) == 1
    assert result.matches[0].quantity == Decimal(5)
    assert result.matches[0].gross_result_brl == Decimal(10)
    assert result.unmatched_quantities == {
        1: Decimal(15),
        2: Decimal(0),
    }


def test_matching_is_isolated_by_date_and_ticker() -> None:
    result = match_day_trades(
        [
            _operation(1, FiscalOperation.BUY, "10", "10"),
            _operation(2, FiscalOperation.SELL, "10", "12", ticker="SMAL11"),
            _operation(
                3,
                FiscalOperation.SELL,
                "10",
                "12",
                trade_date=date(2024, 5, 3),
            ),
        ]
    )

    assert result.matches == ()
    assert result.unmatched_quantities == {
        1: Decimal(10),
        2: Decimal(10),
        3: Decimal(10),
    }
