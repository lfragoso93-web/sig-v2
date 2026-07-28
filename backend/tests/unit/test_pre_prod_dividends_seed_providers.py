from datetime import date

import httpx
import pytest
from app.services.pre_prod_dividends_seed_collector import StrictDividendCollectionError
from app.services.pre_prod_dividends_seed_providers import (
    StrictBrapiDividendProvider,
    StrictYahooDividendProvider,
)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_brapi_stock_adapter_returns_raw_events() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v2/stocks/dividends")
        assert request.url.params["symbols"] == "PETR4"
        return httpx.Response(
            200,
            json={
                "results": [{
                    "symbol": "PETR4",
                    "cashDividends": [{
                        "lastDatePrior": "2026-07-24",
                        "paymentDate": "2026-08-10",
                        "rate": 1.25,
                        "label": "Dividendos",
                    }],
                }],
            },
        )

    async with _client(handler) as client:
        result = await StrictBrapiDividendProvider(
            client=client,
            base_url="https://market.example/api",
            headers={"Authorization": "Bearer token"},
        )("PETR4", "ACAO")

    assert result.source == "brapi"
    assert len(result.rows) == 1
    assert result.rows[0]["eventCategory"] == "cash"
    assert result.empty_reason is None


@pytest.mark.asyncio
async def test_brapi_fii_adapter_uses_fii_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v2/fii/dividends")
        return httpx.Response(200, json={"results": []})

    async with _client(handler) as client:
        result = await StrictBrapiDividendProvider(
            client=client,
            base_url="https://market.example/api",
        )("MXRF11", "FII")

    assert result.rows == ()
    assert result.empty_reason == "provider_returned_no_events"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_brapi_failures_are_blocking(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "failure"})

    async with _client(handler) as client:
        provider = StrictBrapiDividendProvider(
            client=client,
            base_url="https://market.example/api",
        )
        with pytest.raises(StrictDividendCollectionError):
            await provider("PETR4", "ACAO")


@pytest.mark.asyncio
async def test_brapi_invalid_json_is_blocking() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    async with _client(handler) as client:
        provider = StrictBrapiDividendProvider(
            client=client,
            base_url="https://market.example/api",
        )
        with pytest.raises(StrictDividendCollectionError, match="JSON inválido"):
            await provider("PETR4", "ACAO")


@pytest.mark.asyncio
async def test_brapi_missing_ticker_has_explicit_empty_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _client(handler) as client:
        result = await StrictBrapiDividendProvider(
            client=client,
            base_url="https://market.example/api",
        )("OLD3", "ACAO")

    assert result.rows == ()
    assert result.empty_reason == "provider_no_coverage_http_404"


@pytest.mark.asyncio
async def test_yahoo_adapter_uses_national_symbol_and_normalizes_rows() -> None:
    calls: list[str] = []

    async def fetcher(symbol: str):
        calls.append(symbol)
        return [(date(2020, 1, 2), 0.75)]

    result = await StrictYahooDividendProvider(history_fetcher=fetcher)(
        "petr4",
        "acao",
    )

    assert calls == ["PETR4.SA"]
    assert result.source == "yfinance_history"
    assert result.rows == ({
        "paymentDate": "2020-01-02",
        "rate": 0.75,
        "type": "DIVIDENDO",
        "eventCategory": "cash",
    },)


@pytest.mark.asyncio
async def test_yahoo_empty_history_has_explicit_reason() -> None:
    async def fetcher(symbol: str):
        return []

    result = await StrictYahooDividendProvider(history_fetcher=fetcher)(
        "PETR4",
        "ACAO",
    )

    assert result.rows == ()
    assert result.empty_reason == "provider_returned_no_historical_events"


@pytest.mark.asyncio
async def test_yahoo_failure_is_blocking() -> None:
    async def fetcher(symbol: str):
        raise TimeoutError("provider timeout")

    provider = StrictYahooDividendProvider(history_fetcher=fetcher)
    with pytest.raises(StrictDividendCollectionError, match="indisponível"):
        await provider("PETR4", "ACAO")
