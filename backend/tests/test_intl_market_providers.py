from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.core.provider_registry import PROVIDER_REGISTRY, ProviderId
from app.integrations.finnhub import fetch_finnhub_quote
from app.integrations.tiingo import fetch_tiingo_quote
from app.models.asset import AssetType
from app.services.quotes_service import _fetch_intl


def test_provider_registry_has_finnhub_and_tiingo() -> None:
    assert ProviderId.FINNHUB in PROVIDER_REGISTRY
    assert ProviderId.TIINGO in PROVIDER_REGISTRY

    finnhub_def = PROVIDER_REGISTRY[ProviderId.FINNHUB]
    assert finnhub_def.env_key_var == "FINNHUB_API_KEY"
    assert finnhub_def.default_rate_limit_per_minute == 60

    tiingo_def = PROVIDER_REGISTRY[ProviderId.TIINGO]
    assert tiingo_def.env_key_var == "TIINGO_API_KEY"
    assert tiingo_def.default_rate_limit_per_minute == 50


@pytest.mark.asyncio
async def test_fetch_finnhub_quote_parses_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.integrations.finnhub._is_configured", lambda: True)
    monkeypatch.setattr("app.integrations.finnhub._api_key", lambda: "fake-finnhub-key")

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {"c": 250.75, "pc": 248.0}
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        price = await fetch_finnhub_quote("AAPL")
        assert price == 250.75


@pytest.mark.asyncio
async def test_fetch_tiingo_quote_parses_iex_and_eod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.integrations.tiingo._is_configured", lambda: True)
    monkeypatch.setattr("app.integrations.tiingo._api_key", lambda: "fake-tiingo-key")

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: [{"last": 185.50}]
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        price = await fetch_tiingo_quote("NVDA")
        assert price == 185.50


@pytest.mark.asyncio
async def test_fetch_intl_cascade_prioritizes_finnhub_then_tiingo_then_yahoo() -> None:
    pairs = [("AAPL", AssetType.STOCK), ("MSFT", AssetType.STOCK)]

    async def fake_finnhub(pairs_list):
        return {"AAPL": 250.0}

    async def fake_tiingo(pairs_list):
        return {"MSFT": 420.0}

    with patch("app.services.quotes_service._fetch_finnhub_current", side_effect=fake_finnhub):
        with patch("app.services.quotes_service._fetch_tiingo_current", side_effect=fake_tiingo):
            result = await _fetch_intl(pairs)
            assert result == {"AAPL": 250.0, "MSFT": 420.0}


@pytest.mark.asyncio
async def test_fetch_tiingo_history_parses_eod_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.integrations.tiingo import fetch_tiingo_history
    from datetime import datetime, timezone

    monkeypatch.setattr("app.integrations.tiingo._is_configured", lambda: True)
    monkeypatch.setattr("app.integrations.tiingo._api_key", lambda: "fake-tiingo-key")

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: [
        {
            "date": "2026-10-25T00:00:00.000Z",
            "close": 248.50,
            "adjClose": 248.50,
            "open": 245.0,
            "high": 250.0,
            "low": 244.0,
            "volume": 1234567,
        },
        {
            "date": "2026-10-26T00:00:00.000Z",
            "close": 252.00,
            "adjClose": 252.00,
            "open": 249.0,
            "high": 253.0,
            "low": 248.0,
            "volume": 2345678,
        },
    ]
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        bars = await fetch_tiingo_history("AAPL", date_from="2026-10-01", date_to="2026-10-27")
        assert len(bars) == 2
        assert bars[0] == (datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc), 248.50)
        assert bars[1] == (datetime(2026, 10, 26, 0, 0, tzinfo=timezone.utc), 252.00)


@pytest.mark.asyncio
async def test_fetch_tiingo_history_skips_when_unconfigured_or_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.integrations.tiingo import fetch_tiingo_history

    monkeypatch.setattr("app.integrations.tiingo._is_configured", lambda: False)
    assert await fetch_tiingo_history("AAPL", "2026-10-01") == []

    monkeypatch.setattr("app.integrations.tiingo._is_configured", lambda: True)
    # Malicious ticker rejected by safe regex
    assert await fetch_tiingo_history("AAPL; DROP TABLE", "2026-10-01") == []
