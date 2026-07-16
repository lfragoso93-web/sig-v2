from datetime import date
from decimal import Decimal

from app.services.rentabilidade_benchmark_service import _compound_percent, _period_start


def test_compound_percent_uses_effective_monthly_return() -> None:
    result = _compound_percent([Decimal("1.0"), Decimal("1.0")])
    assert result == 2.01


def test_period_start_keeps_requested_month_count() -> None:
    assert _period_start(12, date(2026, 7, 16)) == date(2025, 8, 1)


def test_period_start_zero_means_full_history() -> None:
    assert _period_start(0, date(2026, 7, 16)) is None
