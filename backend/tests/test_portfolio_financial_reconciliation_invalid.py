from copy import deepcopy

import pytest

from app.certification import portfolio_financial_reconciliation as reconciliation


def test_independent_reconciliation_rejects_sale_above_position(monkeypatch):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["transactions"][2]["quantity"] = "151"
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    with pytest.raises(ValueError, match="synthetic sale exceeds position for PETR4"):
        reconciliation.calculate_independent_financial_reconciliation()
