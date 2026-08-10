from datetime import date, datetime, timezone

import pytest

from app.models.asset import AssetType
from app.services import asset_price_gap_sync_service
from app.services.asset_price_coverage_service import CoverageStatus, build_missing_ranges
from app.services.asset_price_gap_sync_service import MissingPriceRange


@pytest.mark.asyncio
async def test_crypto_max_history_marks_start_as_exhausted(monkeypatch) -> None:
    async def fake_fetch_crypto_history(ticker: str):
        assert ticker == "BTC-BRL"
        return (
            [(datetime(2013, 4, 28, tzinfo=timezone.utc), 250.0)],
            "brapi_v2_crypto_max",
            "brapi",
        )

    monkeypatch.setattr(
        asset_price_gap_sync_service,
        "_fetch_crypto_history",
        fake_fetch_crypto_history,
    )

    rows, source, terminal_status, provider = await asset_price_gap_sync_service._fetch_range(
        "BTC-BRL",
        AssetType.CRIPTO,
        MissingPriceRange(
            date_from=date(1900, 1, 1),
            date_to=date(2026, 8, 10),
            reason="missing_all",
        ),
    )

    assert rows == [(datetime(2013, 4, 28, tzinfo=timezone.utc), 250.0)]
    assert source == "brapi_v2_crypto_max"
    assert provider == "brapi"
    assert terminal_status == "HISTORY_START_EXHAUSTED"


def test_exhausted_crypto_start_does_not_request_initial_history_again() -> None:
    ranges = build_missing_ranges(
        status=CoverageStatus.PARTIAL_START,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 8, 10),
        first_price_date=date(2013, 4, 28),
        last_price_date=date(2026, 8, 10),
        provider_status="HISTORY_START_EXHAUSTED",
    )

    assert ranges == ()
