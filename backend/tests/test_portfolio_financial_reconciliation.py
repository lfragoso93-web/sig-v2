from decimal import Decimal

from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_financial_reconciliation,
)
from app.certification.portfolio_seed_asset_policy import syntheticize_ticker
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)


def test_independent_reconciliation_matches_declared_fixture_expectations():
    fixture = load_portfolio_synthetic_certification_fixture()
    declared = fixture["expected"]
    actual = calculate_independent_financial_reconciliation()

    assert set(actual.holdings) == {
        syntheticize_ticker(ticker) for ticker in declared["holdings"]
    }
    for source_ticker, expected in declared["holdings"].items():
        holding = actual.holdings[syntheticize_ticker(source_ticker)]
        assert holding.quantity == Decimal(expected["quantity"])
        assert holding.remaining_cost == Decimal(expected["remaining_cost"])
        assert holding.realized_pnl == Decimal(expected["realized_pnl"])
        assert holding.market_value == Decimal(expected["market_value"])

    totals = declared["totals"]
    assert actual.remaining_cost == Decimal(totals["remaining_cost"])
    assert actual.market_value == Decimal(totals["market_value"])
    assert actual.realized_pnl == Decimal(totals["realized_pnl"])
    assert actual.income == Decimal(totals["income"])
    assert actual.open_pnl == Decimal(totals["open_pnl"])
    assert actual.total_pnl == Decimal(totals["total_pnl"])


def test_independent_reconciliation_proves_full_exit_then_rebuy_resets_cost_basis():
    actual = calculate_independent_financial_reconciliation()
    bova = actual.holdings["CERT303-BOVA11"]

    assert bova.quantity == Decimal("5")
    assert bova.remaining_cost == Decimal("541.00")
    assert bova.realized_pnl == Decimal("198.00")
    assert bova.market_value == Decimal("560.00")
    assert bova.open_pnl == Decimal("19.00")
