from datetime import date

from app.services.portfolio_evolution_period_service import monthly_window_start


def test_monthly_window_uses_exact_calendar_boundaries() -> None:
    today = date(2026, 7, 19)

    assert monthly_window_start(6, today=today) == date(2026, 2, 1)
    assert monthly_window_start(12, today=today) == date(2025, 8, 1)
    assert monthly_window_start(24, today=today) == date(2024, 8, 1)


def test_monthly_window_zero_means_all_history() -> None:
    assert monthly_window_start(0, today=date(2026, 7, 19)) is None
