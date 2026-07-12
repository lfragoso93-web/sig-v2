from datetime import date

import httpx
import pytest

from app.integrations.brapi_v2_client import (
    BrapiV2Client,
    BrapiV2Error,
)


def _mock_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_resolve_tickers_normalizes_and_preserves_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/tickers/resolve"
        assert request.url.params["symbols"] == "VVAR3,PETR4"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "requestedSymbol": "VVAR3",
                        "symbol": "BHIA3",
                        "changed": True,
                        "status": "renamed",
                        "effectiveDate": "2021-08-16",
                    },
                    {
                        "requestedSymbol": "PETR4",
                        "symbol": "PETR4",
                        "changed": False,
                        "status": "active",
                    },
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example/api", token="test-token")
    async with _mock_client(handler) as http_client:
        result = await client.resolve_tickers(
            [" vvar3 ", "PETR4", "vvar3", ""],
            client=http_client,
        )

    assert len(result) == 2
    assert result[0].requested_symbol == "VVAR3"
    assert result[0].symbol == "BHIA3"
    assert result[0].changed is True
    assert result[0].status == "renamed"
    assert result[0].effective_date == date(2021, 8, 16)
    assert result[1].symbol == "PETR4"
    assert result[1].changed is False
    assert result[1].effective_date is None


@pytest.mark.asyncio
async def test_resolve_tickers_splits_requests_into_chunks_of_twenty() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        symbols = request.url.params["symbols"]
        calls.append(symbols)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "requestedSymbol": symbol,
                        "symbol": symbol,
                        "changed": False,
                        "status": "active",
                    }
                    for symbol in symbols.split(",")
                ]
            },
        )

    symbols = [f"TEST{i}" for i in range(21)]
    client = BrapiV2Client(base_url="https://market.example/api", token=None)
    async with _mock_client(handler) as http_client:
        result = await client.resolve_tickers(symbols, client=http_client)

    assert len(calls) == 2
    assert len(calls[0].split(",")) == 20
    assert calls[1] == "TEST20"
    assert len(result) == 21


@pytest.mark.asyncio
async def test_resolve_tickers_ignores_invalid_items_without_failing_batch() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    None,
                    {"requestedSymbol": "PETR4"},
                    {
                        "requestedSymbol": "VALE3",
                        "symbol": "VALE3",
                        "changed": False,
                        "status": "active",
                    },
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        result = await client.resolve_tickers(["PETR4", "VALE3"], client=http_client)

    assert [item.symbol for item in result] == ["VALE3"]


@pytest.mark.asyncio
async def test_resolve_tickers_rejects_invalid_envelope() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        with pytest.raises(BrapiV2Error, match="Resposta inválida"):
            await client.resolve_tickers(["PETR4"], client=http_client)


@pytest.mark.asyncio
async def test_resolve_tickers_normalizes_http_errors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": True})

    client = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        with pytest.raises(BrapiV2Error, match="HTTP 429"):
            await client.resolve_tickers(["PETR4"], client=http_client)
