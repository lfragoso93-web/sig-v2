from unittest.mock import AsyncMock, patch

import pytest

from app.integrations import brapi


@pytest.mark.parametrize("ticker", ["PETR4", "brk.b", "BTC-USD", "A1", "X" * 32])
def test_ticker_path_validator_accepts_supported_symbols(ticker: str) -> None:
    assert brapi._validate_ticker_path_segment(ticker) == ticker


@pytest.mark.parametrize(
    "ticker",
    [
        "",
        "X" * 33,
        "../admin",
        "PETR4/../../admin",
        "PETR4?range=max",
        "PETR4#fragment",
        "https://example.test",
        "PETR4\r\nX-Test: injected",
        "PETR 4",
        "..",
    ],
)
def test_ticker_path_validator_rejects_unsafe_segments(ticker: str) -> None:
    with pytest.raises(ValueError, match="invalid BRAPI ticker"):
        brapi._validate_ticker_path_segment(ticker)


@pytest.mark.parametrize("slug", ["tesouro-selic-01032029", "titulo-1", "x" * 128])
def test_treasury_slug_validator_accepts_supported_slugs(slug: str) -> None:
    assert brapi._validate_treasury_slug_path_segment(slug) == slug


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "x" * 129,
        "../admin",
        "tesouro/../../admin",
        "tesouro?date=2026-01-01",
        "tesouro#fragment",
        "https://example.test",
        "Tesouro-Selic",
        "tesouro\r\nheader",
    ],
)
def test_treasury_slug_validator_rejects_unsafe_segments(slug: str) -> None:
    with pytest.raises(ValueError, match="invalid BRAPI treasury slug"):
        brapi._validate_treasury_slug_path_segment(slug)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("call", "expected"),
    [
        (lambda: brapi.fetch_quotes(["PETR4/../../admin"]), {}),
        (lambda: brapi.fetch_quotes_with_meta(["PETR4?range=max"]), {}),
        (lambda: brapi.fetch_price_history("https://example.test", "2026-01-01", "2026-01-02"), []),
        (lambda: brapi.fetch_price_history_full("PETR4#fragment"), []),
        (lambda: brapi.fetch_asset_info("PETR4\r\nX-Test: injected"), None),
        (lambda: brapi.fetch_treasury_price_by_date("../admin", "2026-01-01"), None),
    ],
)
async def test_unsafe_dynamic_paths_fail_closed_without_http(call, expected) -> None:
    with patch.object(brapi.httpx, "AsyncClient") as client_cls:
        assert await call() == expected
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_treasury_catalog_value_is_validated_before_dynamic_path() -> None:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None

    with (
        patch.object(
            brapi,
            "_load_treasury_catalog",
            new=AsyncMock(return_value={"titulo": "../admin"}),
        ),
        patch.object(brapi.httpx, "AsyncClient", return_value=client),
    ):
        assert await brapi.fetch_treasury_prices(["titulo"]) == {}

    client.get.assert_not_awaited()
