from datetime import date, datetime, timezone

import pytest

from app.models.asset import AssetType
from app.services import asset_price_gap_sync_service
from app.services.asset_price_coverage_service import CoverageStatus, build_missing_ranges
from app.services.asset_price_gap_sync_service import MissingPriceRange


@pytest.mark.asyncio
async def test_crypto_max_history_marks_small_complete_result_as_exhausted(monkeypatch) -> None:
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


@pytest.mark.asyncio
async def test_crypto_max_history_does_not_mark_exact_1000_rows_as_exhausted(monkeypatch) -> None:
    async def fake_fetch_crypto_history(ticker: str):
        assert ticker == "BTC-BRL"
        start = datetime(2023, 11, 15, tzinfo=timezone.utc)
        return (
            [(start.replace(day=start.day), float(index + 1)) for index in range(1000)],
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

    assert len(rows) == 1000
    assert source == "brapi_v2_crypto_max"
    assert provider == "brapi"
    assert terminal_status == "HISTORY_START_TRUNCATED"


@pytest.mark.asyncio
async def test_truncated_crypto_start_uses_yahoo_usd_ptax_complement_and_keeps_brapi_primary(monkeypatch) -> None:
    usd_rows = [
        (datetime(2014, 9, 17, tzinfo=timezone.utc), 400.0),
        (datetime(2023, 11, 15, tzinfo=timezone.utc), 35000.0),
    ]
    brl_rows = [
        (datetime(2014, 9, 17, tzinfo=timezone.utc), 960.0),
        (datetime(2023, 11, 15, tzinfo=timezone.utc), 171500.0),
    ]

    async def fake_yahoo_max(symbol: str, asset_type: AssetType):
        assert symbol == "BTC-USD"
        assert asset_type == AssetType.CRIPTO
        return usd_rows

    async def fake_convert(rows):
        assert rows == usd_rows
        return brl_rows

    async def fail_brapi(_: str):
        raise AssertionError("BRAPI max must not be retried for truncated missing_start")

    monkeypatch.setattr(asset_price_gap_sync_service, "_fetch_yf_max", fake_yahoo_max)
    monkeypatch.setattr(
        asset_price_gap_sync_service,
        "_convert_crypto_usd_rows_to_brl",
        fake_convert,
    )
    monkeypatch.setattr(asset_price_gap_sync_service, "_fetch_crypto_history", fail_brapi)

    rows, source, terminal_status, provider = await asset_price_gap_sync_service._fetch_range(
        "BTC-BRL",
        AssetType.CRIPTO,
        MissingPriceRange(
            date_from=date(1900, 1, 1),
            date_to=date(2023, 11, 20),
            reason="missing_start",
        ),
        crypto_start_truncated=True,
    )

    assert rows == brl_rows
    assert source == "yfinance_crypto_ptax_brl_max"
    assert len(source) <= 30
    assert provider == "brapi"
    assert terminal_status == "HISTORY_START_EXHAUSTED"


@pytest.mark.asyncio
async def test_empty_truncated_crypto_complement_keeps_truncated_status(monkeypatch) -> None:
    async def fake_yahoo_max(symbol: str, asset_type: AssetType):
        assert symbol == "BTC-USD"
        assert asset_type == AssetType.CRIPTO
        return []

    async def fake_convert(rows):
        assert rows == []
        return []

    monkeypatch.setattr(asset_price_gap_sync_service, "_fetch_yf_max", fake_yahoo_max)
    monkeypatch.setattr(
        asset_price_gap_sync_service,
        "_convert_crypto_usd_rows_to_brl",
        fake_convert,
    )

    rows, source, terminal_status, provider = await asset_price_gap_sync_service._fetch_range(
        "BTC-BRL",
        AssetType.CRIPTO,
        MissingPriceRange(
            date_from=date(1900, 1, 1),
            date_to=date(2023, 11, 20),
            reason="missing_start",
        ),
        crypto_start_truncated=True,
    )

    assert rows == []
    assert source == "yfinance_crypto_ptax_brl_max"
    assert len(source) <= 30
    assert provider == "brapi"
    assert terminal_status == "HISTORY_START_TRUNCATED"


def test_complement_source_fits_asset_price_schema() -> None:
    source_column = asset_price_gap_sync_service.AssetPrice.__table__.c.source
    source = "yfinance_crypto_ptax_brl_max"

    assert source_column.type.length == 30
    assert len(source) == 28
    assert len(source) <= source_column.type.length
    assert "yfinance" in source
    assert "crypto" in source
    assert "ptax" in source
    assert "brl" in source


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
