from datetime import date, datetime, timezone

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import (
    AssetPriceCoverage,
    CoverageRange,
    CoverageStatus,
    build_missing_ranges,
)
from app.services.asset_price_gap_sync_service import build_missing_edge_ranges


def test_provider_exhausted_start_does_not_repeat_old_history() -> None:
    ranges = build_missing_ranges(
        status=CoverageStatus.PARTIAL_START,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 7, 14),
        first_price_date=date(2020, 2, 10),
        last_price_date=date(2026, 7, 13),
        provider_status="HISTORY_START_EXHAUSTED",
    )
    assert ranges == ()


def test_stale_end_is_still_synced_after_start_exhaustion() -> None:
    ranges = build_missing_ranges(
        status=CoverageStatus.PARTIAL_BOTH,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 7, 14),
        first_price_date=date(2020, 2, 10),
        last_price_date=date(2026, 6, 30),
        provider_status="HISTORY_START_EXHAUSTED",
    )
    assert len(ranges) == 1
    assert ranges[0].reason == "stale_end"
    assert ranges[0].date_to == date(2026, 7, 14)


def test_coverage_exposes_exact_ranges_and_provider_metadata() -> None:
    coverage = AssetPriceCoverage(
        ticker="PETR4",
        asset_type=AssetType.ACAO.value,
        asset_id=10,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 14),
        first_price_date=date(2021, 1, 1),
        last_price_date=date(2026, 7, 13),
        price_count=1000,
        status=CoverageStatus.PARTIAL_START,
        needs_sync=True,
        missing_ranges=(CoverageRange(date(2020, 1, 1), date(2021, 1, 6), "missing_start"),),
        provider="brapi",
        provider_symbol="PETR4",
        provider_status="OK",
        provider_last_sync_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        provider_attempts=2,
    )
    payload = coverage.to_dict()
    assert payload["provider_symbol"] == "PETR4"
    assert payload["missing_ranges"][0]["reason"] == "missing_start"
    assert build_missing_edge_ranges(coverage)[0].date_from == date(2020, 1, 1)


def test_no_quote_type_has_no_ranges() -> None:
    ranges = build_missing_ranges(
        status=CoverageStatus.NO_MARKET_QUOTE,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 14),
        first_price_date=None,
        last_price_date=None,
    )
    assert ranges == ()
