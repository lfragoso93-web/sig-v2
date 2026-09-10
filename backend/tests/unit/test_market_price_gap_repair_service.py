from datetime import date, datetime, timezone

from app.services.market_price_gap_repair_service import _needs_b3_backfill


def test_needs_b3_backfill_when_provider_series_ends_before_target() -> None:
    assert _needs_b3_backfill(
        provider_rows=[(datetime(2025, 10, 2, tzinfo=timezone.utc), 6.65)],
        transaction_start=date(2024, 11, 6),
        target_end=date(2026, 9, 10),
        first_price=datetime(2017, 9, 15, tzinfo=timezone.utc),
        last_price=datetime(2025, 10, 2, tzinfo=timezone.utc),
    )


def test_needs_b3_backfill_is_false_when_series_covers_window() -> None:
    assert not _needs_b3_backfill(
        provider_rows=[(datetime(2026, 9, 10, tzinfo=timezone.utc), 10.0)],
        transaction_start=date(2024, 11, 6),
        target_end=date(2026, 9, 10),
        first_price=datetime(2017, 9, 15, tzinfo=timezone.utc),
        last_price=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )


def test_needs_b3_backfill_when_series_starts_after_first_transaction() -> None:
    assert _needs_b3_backfill(
        provider_rows=[(datetime(2025, 1, 2, tzinfo=timezone.utc), 10.0)],
        transaction_start=date(2024, 11, 6),
        target_end=date(2025, 1, 2),
        first_price=datetime(2025, 1, 2, tzinfo=timezone.utc),
        last_price=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
