from datetime import date, datetime, timezone

import pytest

from app.models.asset import AssetType
from app.services import asset_price_gap_sync_service
from app.services.asset_price_coverage_service import CoverageStatus, build_missing_ranges
from app.services.asset_price_gap_sync_service import MissingPriceRange


@pytest.mark.asyncio
async def test_missing_all_crypto_falls_back_to_yahoo_usd_ptax_when_brapi_is_empty(monkeypatch) -> None:
    import app.integrations.brapi_crypto_history as brapi_crypto_history

    usd_rows = [
        (datetime(2024, 1, 1, tzinfo=timezone.utc), 1.0),
        (datetime(2024, 1, 2, tzinfo=timezone.utc), 1.1),
    ]
    brl_rows = [
        (datetime(2024, 1, 1, tzinfo=timezone.utc), 4.90),
        (datetime(2024, 1, 2, tzinfo=timezone.utc), 5.40),
    ]

    async def fake_brapi(*args, **kwargs):
        return []

    async def fake_yahoo(symbol: str, asset_type: AssetType):
        assert symbol == "BFUSD-USD"
        assert asset_type == AssetType.CRIPTO
        return usd_rows

    async def fake_convert(rows):
        assert rows == usd_rows
        return brl_rows

    monkeypatch.setattr(brapi_crypto_history, "fetch_brapi_crypto_history", fake_brapi)
    monkeypatch.setattr(asset_price_gap_sync_service, "_fetch_yf_max", fake_yahoo)
    monkeypatch.setattr(asset_price_gap_sync_service, "_convert_crypto_usd_rows_to_brl", fake_convert)

    rows, source, provider = await asset_price_gap_sync_service._fetch_crypto_history("BFUSD-BRL")

    assert rows == brl_rows
    assert source == "yfinance_crypto_ptax_brl_max"
    assert provider == "yfinance"


@pytest.mark.asyncio
async def test_missing_all_crypto_with_no_brapi_or_yahoo_data_is_terminal_unavailable(monkeypatch) -> None:
    import app.integrations.brapi_crypto_history as brapi_crypto_history

    async def fake_brapi(*args, **kwargs):
        return []

    async def fake_yahoo(symbol: str, asset_type: AssetType):
        assert symbol == "XUSD-USD"
        assert asset_type == AssetType.CRIPTO
        return []

    monkeypatch.setattr(brapi_crypto_history, "fetch_brapi_crypto_history", fake_brapi)
    monkeypatch.setattr(asset_price_gap_sync_service, "_fetch_yf_max", fake_yahoo)

    rows, source, terminal_status, provider = await asset_price_gap_sync_service._fetch_range(
        "XUSD-BRL",
        AssetType.CRIPTO,
        MissingPriceRange(
            date_from=date(1900, 1, 1),
            date_to=date(2026, 8, 10),
            reason="missing_all",
        ),
    )

    assert rows == []
    assert source == "yfinance_crypto_ptax_brl_max"
    assert provider == "yfinance"
    assert terminal_status == "HISTORY_UNAVAILABLE"

    ranges = build_missing_ranges(
        status=CoverageStatus.MISSING,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 8, 10),
        first_price_date=None,
        last_price_date=None,
        provider_status="HISTORY_UNAVAILABLE",
    )
    assert ranges == ()
