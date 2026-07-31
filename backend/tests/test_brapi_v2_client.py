from datetime import date

import httpx
import pytest

from app.integrations.brapi_v2_client import (
    BrapiV2AuthenticationError,
    BrapiV2Client,
    BrapiV2ContractError,
    BrapiV2Error,
    BrapiV2PermissionError,
    BrapiV2RateLimitError,
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
        with pytest.raises(BrapiV2Error, match="Resposta invalida"):
            await client.resolve_tickers(["PETR4"], client=http_client)


@pytest.mark.asyncio
async def test_resolve_tickers_normalizes_http_errors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": True})

    client = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        with pytest.raises(BrapiV2Error, match="HTTP 429"):
            await client.resolve_tickers(["PETR4"], client=http_client)


@pytest.mark.asyncio
async def test_ticker_coverage_exposes_capabilities_and_renamed_symbol() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/tickers/coverage"
        assert request.url.params["symbols"] == "VVAR3,MXRF11"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "requestedSymbol": "VVAR3",
                        "symbol": "BHIA3",
                        "changed": True,
                        "status": "renamed",
                        "assetType": "stock",
                        "subType": "stock",
                        "availableData": {
                            "quote": True,
                            "historical": True,
                            "stockDividends": True,
                            "fiiDividends": False,
                        },
                        "recommendedEndpoints": {
                            "dividends": "/api/v2/stocks/dividends?symbols=BHIA3"
                        },
                    },
                    {
                        "requestedSymbol": "MXRF11",
                        "symbol": "MXRF11",
                        "changed": False,
                        "status": "active",
                        "assetType": "fund",
                        "subType": "fii",
                        "availableData": {"fiiDividends": True},
                        "recommendedEndpoints": {},
                    },
                ]
            },
        )

    brapi = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        result = await brapi.get_ticker_coverage(
            [" vvar3 ", "MXRF11"], client=http_client
        )

    assert result[0].symbol == "BHIA3"
    assert result[0].status == "renamed"
    assert result[0].supports("stockDividends") is True
    assert result[0].supports("fiiDividends") is False
    assert result[1].sub_type == "fii"
    assert result[1].supports("fiiDividends") is True


@pytest.mark.asyncio
async def test_ticker_coverage_preserves_unknown_symbol() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "requestedSymbol": "INVALID",
                        "status": "unknown",
                        "availableData": {},
                        "recommendedEndpoints": {},
                    }
                ]
            },
        )

    brapi = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        result = await brapi.get_ticker_coverage(["INVALID"], client=http_client)

    assert result[0].requested_symbol == "INVALID"
    assert result[0].symbol == "INVALID"
    assert result[0].status == "unknown"
    assert result[0].available_data == {}


@pytest.mark.asyncio
async def test_list_ticker_renames_applies_documented_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["symbols"] == "VVAR3,BHIA3"
        assert request.url.params["startDate"] == "2020-01-01"
        assert request.url.params["endDate"] == "2022-12-31"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "oldSymbol": "VVAR3",
                        "newSymbol": "BHIA3",
                        "canonicalSymbol": "BHIA3",
                        "effectiveDate": "2021-08-16",
                    }
                ]
            },
        )

    brapi = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        result = await brapi.list_ticker_renames(
            symbols=["VVAR3", "BHIA3"],
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
            client=http_client,
        )

    assert result[0].old_symbol == "VVAR3"
    assert result[0].canonical_symbol == "BHIA3"
    assert result[0].effective_date == date(2021, 8, 16)


@pytest.mark.asyncio
async def test_list_tickers_returns_typed_pagination() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["type"] == "fund"
        assert request.url.params["subType"] == "fii"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "MXRF11",
                        "name": "Maxi Renda",
                        "assetType": "fund",
                        "subType": "fii",
                        "exchange": "B3",
                        "currency": "BRL",
                        "isActive": True,
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 100,
                    "totalItems": 1,
                    "totalPages": 1,
                    "hasNextPage": False,
                },
            },
        )

    brapi = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        result = await brapi.list_tickers(
            asset_type="fund", sub_type="fii", limit=100, client=http_client
        )

    assert result.results[0].symbol == "MXRF11"
    assert result.results[0].sub_type == "fii"
    assert result.total_items == 1
    assert result.has_next_page is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, BrapiV2AuthenticationError),
        (403, BrapiV2PermissionError),
        (429, BrapiV2RateLimitError),
    ],
)
async def test_client_classifies_provider_http_errors(
    status_code: int, error_type: type[BrapiV2Error]
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": True})

    brapi = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        with pytest.raises(error_type) as exc_info:
            await brapi.get_ticker_coverage(["PETR4"], client=http_client)

    assert exc_info.value.status_code == status_code


@pytest.mark.asyncio
async def test_coverage_rejects_malformed_capability_contract() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "requestedSymbol": "PETR4",
                        "symbol": "PETR4",
                        "status": "active",
                        "availableData": [],
                    }
                ]
            },
        )

    brapi = BrapiV2Client(base_url="https://market.example/api")
    async with _mock_client(handler) as http_client:
        with pytest.raises(BrapiV2ContractError, match="Resposta invalida"):
            await brapi.get_ticker_coverage(["PETR4"], client=http_client)
