from copy import deepcopy
from decimal import Decimal

from app.certification import portfolio_financial_reconciliation as reconciliation


def test_independent_reconciliation_keeps_realized_pnl_from_fully_closed_position(monkeypatch):
    fixture = deepcopy(reconciliation.load_portfolio_synthetic_certification_fixture())
    fixture["transactions"] = [
        row for row in fixture["transactions"] if row["ticker"] == "BOVA11"
    ][:-1]
    fixture["market_prices"]["prices"] = {}
    fixture["income_events"] = []
    monkeypatch.setattr(
        reconciliation,
        "load_portfolio_synthetic_certification_fixture",
        lambda: fixture,
    )

    actual = reconciliation.calculate_independent_financial_reconciliation()

    assert actual.holdings == {}
    assert actual.realized_pnl == Decimal("198.00")
    assert actual.open_pnl == Decimal("0.00")
    assert actual.total_pnl == Decimal("198.00")
