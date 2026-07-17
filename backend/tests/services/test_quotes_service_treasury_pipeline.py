from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services import quotes_service


@pytest.mark.asyncio
async def test_treasury_current_price_uses_official_fallback(monkeypatch):
    primary = AsyncMock(return_value={})
    fallback = AsyncMock(
        return_value={"tesouro-renda-mais-2065": 1110.25}
    )
    monkeypatch.setattr(
        quotes_service,
        "brapi_fetch_treasury_prices",
        primary,
    )
    monkeypatch.setattr(
        quotes_service,
        "fetch_tesouro_transparente_prices",
        fallback,
    )

    prices = await quotes_service._fetch_treasury_prices(
        ["TESOURO-RENDA-MAIS-2065"]
    )

    assert prices == {"TESOURO-RENDA-MAIS-2065": 1110.25}
    primary.assert_awaited_once_with(["tesouro-renda-mais-2065"])
    fallback.assert_awaited_once_with(["tesouro-renda-mais-2065"])


@pytest.mark.asyncio
async def test_treasury_fallback_requests_only_missing_symbols(monkeypatch):
    primary = AsyncMock(
        return_value={"tesouro-selic-01032031": 19380.19}
    )
    fallback = AsyncMock(
        return_value={"tesouro-renda-mais-2060": 1245.60}
    )
    monkeypatch.setattr(
        quotes_service,
        "brapi_fetch_treasury_prices",
        primary,
    )
    monkeypatch.setattr(
        quotes_service,
        "fetch_tesouro_transparente_prices",
        fallback,
    )

    prices = await quotes_service._fetch_treasury_prices(
        ["TESOURO-SELIC-01032031", "TESOURO-RENDA-MAIS-2060"]
    )

    assert prices == {
        "TESOURO-SELIC-01032031": 19380.19,
        "TESOURO-RENDA-MAIS-2060": 1245.60,
    }
    fallback.assert_awaited_once_with(["tesouro-renda-mais-2060"])


def test_treasury_database_lookup_is_case_insensitive():
    statement = quotes_service._asset_lookup_stmt(
        "TESOURO-RENDA-MAIS-2065",
        AssetType.TESOURO_DIRETO,
    )

    sql = str(statement).lower()
    assert "lower(assets.ticker)" in sql
