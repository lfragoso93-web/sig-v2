from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_financial_reconciliation,
)


def test_independent_reconciliation_uses_persisted_synthetic_tickers():
    actual = calculate_independent_financial_reconciliation()

    assert actual.holdings
    assert all(ticker.startswith("CERT303-") for ticker in actual.holdings)
    assert "PETR4" not in actual.holdings
    assert "CERT303-PETR4" in actual.holdings
