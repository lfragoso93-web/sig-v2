from copy import deepcopy

import pytest

from app.certification import portfolio_financial_reconciliation as reconciliation


def test_independent_reconciliation_fails_when_open_position_has_no_expected_price(monkeypatch):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["market_prices"]["prices"].pop("PETR4")
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    with pytest.raises(ValueError, match="missing expected market price for CERT303-PETR4"):
        reconciliation.calculate_independent_financial_reconciliation()
