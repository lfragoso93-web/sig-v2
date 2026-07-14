from datetime import date

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import (
    AssetPriceCoverage,
    CoverageStatus,
    classify_coverage,
)
from app.services.asset_price_gap_sync_service import build_missing_edge_ranges
from app.services.asset_price_global_backfill_service import MAX_HISTORY_START


def test_global_history_policy_starts_before_modern_assets() -> None:
    assert MAX_HISTORY_START == date(1900, 1, 1)


def test_existing_recent_history_is_partial_under_global_policy() -> None:
    status = classify_coverage(
        asset_type=AssetType.ACAO,
        asset_exists=True,
        required_from=MAX_HISTORY_START,
        required_to=date(2026, 7, 13),
        first_price_date=date(2020, 1, 2),
        last_price_date=date(2026, 7, 10),
    )

    assert status == CoverageStatus.PARTIAL_START


def test_global_missing_asset_requests_full_available_interval() -> None:
    coverage = AssetPriceCoverage(
        ticker="TEST3",
        asset_type=AssetType.ACAO.value,
        asset_id=10,
        required_from=MAX_HISTORY_START,
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
        price_count=0,
        status=CoverageStatus.MISSING,
        needs_sync=True,
    )

    ranges = build_missing_edge_ranges(coverage)

    assert len(ranges) == 1
    assert ranges[0].date_from == MAX_HISTORY_START
    assert ranges[0].date_to == date(2026, 7, 13)
    assert ranges[0].reason == "missing_all"


def test_no_quote_asset_stays_out_of_global_provider_sync() -> None:
    status = classify_coverage(
        asset_type=AssetType.RENDA_FIXA,
        asset_exists=True,
        required_from=MAX_HISTORY_START,
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.NO_MARKET_QUOTE
