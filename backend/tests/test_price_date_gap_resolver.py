from datetime import date
from pathlib import Path

from app.services.price_date_gap_resolver_service import (
    POINT_GAP_LOOKBACK_DAYS,
    _bounded_window,
)


RESOLVER_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "price_date_gap_resolver_service.py"
)
PRICE_HISTORY_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "price_history_service.py"
)


def test_point_gap_window_is_bounded_to_five_days() -> None:
    target = date(2026, 8, 7)
    start, end = _bounded_window(target)

    assert POINT_GAP_LOOKBACK_DAYS == 5
    assert end == target
    assert (end - start).days == 5


def test_resolver_is_read_first_persist_then_read_again() -> None:
    source = RESOLVER_PATH.read_text(encoding="utf-8")
    function = source.split("async def resolve_price_at_date_gap", 1)[1]

    first_read = function.index("existing = await get_price_at_date")
    provider_fetch = function.index("rows, source = await _fetch_window")
    persistence = function.index("await _persist_window")
    second_read = function.index("resolved = await get_price_at_date")

    assert first_read < provider_fetch < persistence < second_read
    assert "period=\"max\"" not in source
    assert "stale_snapshot" not in source
    assert "run_global_asset_price_backfill" not in source


def test_pure_price_reader_does_not_import_gap_resolver() -> None:
    source = PRICE_HISTORY_PATH.read_text(encoding="utf-8")
    assert "price_date_gap_resolver_service" not in source
