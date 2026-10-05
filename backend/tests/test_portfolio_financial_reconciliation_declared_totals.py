from decimal import Decimal

from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_financial_reconciliation,
)


def test_independent_reconciliation_exact_cert303_totals():
    actual = calculate_independent_financial_reconciliation()

    assert actual.remaining_cost == Decimal("37629.30")
    assert actual.market_value == Decimal("38960.00")
    assert actual.realized_pnl == Decimal("450.80")
    assert actual.open_pnl == Decimal("1330.70")
    assert actual.income == Decimal("20.00")
    assert actual.total_pnl == Decimal("1801.50")