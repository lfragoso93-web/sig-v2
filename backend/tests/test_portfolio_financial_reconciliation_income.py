from decimal import Decimal

from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_financial_reconciliation,
)


def test_independent_reconciliation_keeps_income_outside_price_pnl():
    actual = calculate_independent_financial_reconciliation()

    price_pnl = actual.realized_pnl + actual.open_pnl
    assert price_pnl == Decimal("1781.50")
    assert actual.income == Decimal("20.00")
    assert actual.total_pnl == price_pnl + actual.income == Decimal("1801.50")
