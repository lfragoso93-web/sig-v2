from copy import deepcopy

import pytest

from app.certification import portfolio_financial_reconciliation as reconciliation


@pytest.mark.parametrize(
    ("field", "value"),
    [("quantity", "0"), ("price", "-1"), ("fees", "-0.01")],
)
def test_independent_reconciliation_rejects_invalid_transaction_values(
    monkeypatch, field, value
):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["transactions"][0][field] = value
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    with pytest.raises(ValueError, match="invalid synthetic transaction values for PETR4"):
        reconciliation.calculate_independent_financial_reconciliation()
