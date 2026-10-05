from copy import deepcopy

import pytest

from app.certification import portfolio_financial_reconciliation as reconciliation


@pytest.mark.parametrize("ticker", ["", "CERT303-PETR4"])
def test_independent_reconciliation_rejects_invalid_source_ticker(monkeypatch, ticker):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["transactions"][0]["ticker"] = ticker
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    with pytest.raises(ValueError, match="invalid source ticker"):
        reconciliation.calculate_independent_financial_reconciliation()
