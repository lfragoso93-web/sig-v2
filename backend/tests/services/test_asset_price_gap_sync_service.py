from datetime import date

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import AssetPriceCoverage, CoverageStatus
from app.services.asset_price_gap_sync_service import build_missing_edge_ranges


def _coverage(
    *,
    status: CoverageStatus,
    required_from: date | None = date(2024, 1, 1),
    required_to: date = date(2026, 7, 13),
    first_price_date: date | None = None,
    last_price_date: date | None = None,
    asset_id: int | None = 1,
    asset_type: str = AssetType.ACAO.value,
    needs_sync: bool = True,
) -> AssetPriceCoverage:
    return AssetPriceCoverage(
        ticker="TEST3",
        asset_type=asset_type,
        asset_id=asset_id,
        required_from=required_from,
        required_to=required_to,
        first_price_date=first_price_date,
        last_price_date=last_price_date,
        price_count=0,
        status=status,
        needs_sync=needs_sync,
    )


def test_missing_history_requests_entire_required_period() -> None:
    ranges = build_missing_edge_ranges(_coverage(status=CoverageStatus.MISSING))

    assert len(ranges) == 1
    assert ranges[0].date_from == date(2024, 1, 1)
    assert ranges[0].date_to == date(2026, 7, 13)
    assert ranges[0].reason == "missing_all"


def test_partial_start_requests_only_missing_start_with_overlap() -> None:
    ranges = build_missing_edge_ranges(
        _coverage(
            status=CoverageStatus.PARTIAL_START,
            first_price_date=date(2025, 1, 10),
            last_price_date=date(2026, 7, 10),
        )
    )

    assert len(ranges) == 1
    assert ranges[0].date_from == date(2024, 1, 1)
    assert ranges[0].date_to == date(2025, 1, 15)
    assert ranges[0].reason == "missing_start"


def test_stale_history_requests_only_tail_with_overlap() -> None:
    ranges = build_missing_edge_ranges(
        _coverage(
            status=CoverageStatus.STALE,
            first_price_date=date(2023, 1, 1),
            last_price_date=date(2026, 6, 30),
        )
    )

    assert len(ranges) == 1
    assert ranges[0].date_from == date(2026, 6, 25)
    assert ranges[0].date_to == date(2026, 7, 13)
    assert ranges[0].reason == "stale_end"


def test_partial_both_requests_two_edge_ranges() -> None:
    ranges = build_missing_edge_ranges(
        _coverage(
            status=CoverageStatus.PARTIAL_BOTH,
            first_price_date=date(2025, 1, 10),
            last_price_date=date(2026, 6, 30),
        )
    )

    assert [item.reason for item in ranges] == ["missing_start", "stale_end"]
    assert ranges[0].date_from == date(2024, 1, 1)
    assert ranges[0].date_to == date(2025, 1, 15)
    assert ranges[1].date_from == date(2026, 6, 25)
    assert ranges[1].date_to == date(2026, 7, 13)


def test_complete_or_no_quote_asset_has_no_ranges() -> None:
    complete = build_missing_edge_ranges(
        _coverage(status=CoverageStatus.COMPLETE, needs_sync=False)
    )
    no_quote = build_missing_edge_ranges(
        _coverage(
            status=CoverageStatus.NO_MARKET_QUOTE,
            asset_type=AssetType.RENDA_FIXA.value,
        )
    )

    assert complete == ()
    assert no_quote == ()


def test_missing_catalog_asset_is_not_sent_to_provider() -> None:
    ranges = build_missing_edge_ranges(
        _coverage(status=CoverageStatus.MISSING_ASSET, asset_id=None)
    )

    assert ranges == ()


def test_missing_history_without_required_start_is_skipped() -> None:
    ranges = build_missing_edge_ranges(
        _coverage(status=CoverageStatus.MISSING, required_from=None)
    )

    assert ranges == ()
