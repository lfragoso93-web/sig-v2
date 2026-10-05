from datetime import date

from app.services.lifecycle_aware_price_service import _is_stale_price_usable


def test_stale_price_is_usable_inside_market_staleness_window() -> None:
    assert _is_stale_price_usable(
        last_price_date=date(2025, 10, 2),
        target_date=date(2025, 11, 25),
    )


def test_stale_price_is_not_usable_after_market_staleness_window() -> None:
    assert not _is_stale_price_usable(
        last_price_date=date(2025, 10, 2),
        target_date=date(2026, 1, 15),
    )


def test_future_price_is_not_usable_as_stale_fallback() -> None:
    assert not _is_stale_price_usable(
        last_price_date=date(2025, 10, 3),
        target_date=date(2025, 10, 2),
    )
