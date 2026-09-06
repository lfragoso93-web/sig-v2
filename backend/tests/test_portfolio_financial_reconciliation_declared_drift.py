from copy import deepcopy

import pytest

from app.certification.portfolio_financial_reconciliation import (
    assert_declared_financial_expectations,
    calculate_independent_financial_reconciliation,
)
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)


def test_declared_expectation_drift_fails_closed():
    fixture = deepcopy(load_portfolio_synthetic_certification_fixture())
    actual = calculate_independent_financial_reconciliation()
    fixture["expected"]["holdings"]["PETR4"]["remaining_cost"] = "1905.00"

    with pytest.raises(ValueError, match="CERT303-PETR4:remaining_cost"):
        assert_declared_financial_expectations(fixture, actual)
