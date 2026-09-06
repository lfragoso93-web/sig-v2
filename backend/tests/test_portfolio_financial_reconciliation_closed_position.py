from copy import deepcopy
from decimal import Decimal

from app.certification import portfolio_financial_reconciliation as reconciliation


def test_independent_reconciliation_keeps_realized_pnl_from_fully_closed_position(monkeypatch):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["transactions"] = fixture["transactions"][:-1]
    fixture["market_prices"]["prices"].pop("BOVA11")
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    actual = reconciliation.calculate_independent_financial_reconciliation()

    assert "CERT303-BOVA11" not in actual.holdings
    assert actual.realized_pnl == Decimal("491.00")
