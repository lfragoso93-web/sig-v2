from datetime import date

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import (
    CoverageStatus,
    classify_coverage,
)


def test_no_quote_type_never_requires_market_sync() -> None:
    status = classify_coverage(
        asset_type=AssetType.RENDA_FIXA,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.NO_MARKET_QUOTE


def test_missing_asset_is_reported_before_price_coverage() -> None:
    status = classify_coverage(
        asset_type=AssetType.ACAO,
        asset_exists=False,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.MISSING_ASSET


def test_asset_without_prices_is_missing() -> None:
    status = classify_coverage(
        asset_type=AssetType.FII,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.MISSING


def test_history_missing_at_start_is_partial_start() -> None:
    status = classify_coverage(
        asset_type=AssetType.ETF_NACIONAL,
        asset_exists=True,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=date(2025, 1, 1),
        last_price_date=date(2026, 7, 10),
    )

    assert status == CoverageStatus.PARTIAL_START


def test_old_last_price_is_stale() -> None:
    status = classify_coverage(
        asset_type=AssetType.STOCK,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=date(2024, 1, 1),
        last_price_date=date(2026, 6, 30),
    )

    assert status == CoverageStatus.STALE


def test_missing_both_edges_is_partial_both() -> None:
    status = classify_coverage(
        asset_type=AssetType.CRIPTO,
        asset_exists=True,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=date(2025, 1, 1),
        last_price_date=date(2026, 6, 1),
    )

    assert status == CoverageStatus.PARTIAL_BOTH


def test_small_calendar_gap_is_complete() -> None:
    status = classify_coverage(
        asset_type=AssetType.ACAO,
        asset_exists=True,
        required_from=date(2025, 1, 4),
        required_to=date(2026, 7, 13),
        first_price_date=date(2025, 1, 6),
        last_price_date=date(2026, 7, 10),
    )

    assert status == CoverageStatus.COMPLETE
