from copy import deepcopy

import pytest

from app.certification import portfolio_financial_reconciliation as reconciliation


def test_independent_reconciliation_rejects_unsupported_operation(monkeypatch):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["transactions"][0]["operation"] = "transfer"
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    with pytest.raises(ValueError, match="unsupported synthetic operation: transfer"):
        reconciliation.calculate_independent_financial_reconciliation()
