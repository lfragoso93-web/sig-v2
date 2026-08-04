"""Testes da projeção mensal quantitativa de Day Trade."""

from datetime import date
from decimal import Decimal

from app.services.irpf_day_trade_matcher import (
    FiscalOperation,
    FiscalTradeOperation,
)
from app.services.irpf_day_trade_monthly_projection import (
    project_day_trades_by_month,
)


def _operation(
    transaction_id: int,
    operation: FiscalOperation,
    quantity: str,
    price: str,
    trade_date: date,
) -> FiscalTradeOperation:
    return FiscalTradeOperation(
        transaction_id=transaction_id,
        ticker="BOVA11",
        trade_date=trade_date,
        operation=operation,
        quantity=Decimal(quantity),
        unit_price_brl=Decimal(price),
    )


def test_projection_separates_intraday_match_and_swing_remainder() -> None:
    projection = project_day_trades_by_month(
        [
            _operation(1, FiscalOperation.BUY, "20", "10", date(2024, 5, 2)),
            _operation(2, FiscalOperation.SELL, "5", "12", date(2024, 5, 2)),
        ]
    )

    month = projection[0]
    assert month.competence_month == "2024-05"
    assert month.matched_quantity == Decimal(5)
    assert month.day_trade_result_brl == Decimal(10)
    assert month.unmatched_buy_quantity == Decimal(15)
    assert month.unmatched_sell_quantity == Decimal(0)


def test_projection_aggregates_multiple_competences() -> None:
    projection = project_day_trades_by_month(
        [
            _operation(1, FiscalOperation.BUY, "10", "10", date(2024, 5, 2)),
            _operation(2, FiscalOperation.SELL, "10", "11", date(2024, 5, 2)),
            _operation(3, FiscalOperation.SELL, "3", "12", date(2024, 6, 3)),
        ]
    )

    assert [item.competence_month for item in projection] == ["2024-05", "2024-06"]
    assert projection[0].matched_quantity == Decimal(10)
    assert projection[1].unmatched_sell_quantity == Decimal(3)
