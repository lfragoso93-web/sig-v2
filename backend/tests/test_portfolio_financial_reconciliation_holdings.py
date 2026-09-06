from decimal import Decimal

from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_financial_reconciliation,
)


def test_independent_reconciliation_open_pnl_by_holding():
    actual = calculate_independent_financial_reconciliation()
    expected = {
        "PETR4": Decimal("255.00"),
        "MXRF11": Decimal("98.00"),
        "BOVA11": Decimal("19.00"),
        "AAPL34": Decimal("-61.50"),
        "BTC": Decimal("980.00"),
        "TESOURO-SELIC-2029": Decimal("-50.00"),
        "CDB-SYN-CDI-2028": Decimal("50.00"),
    }

    assert {ticker: holding.open_pnl for ticker, holding in actual.holdings.items()} == expected
