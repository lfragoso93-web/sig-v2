"""Testes unitarios para cliente v2 tipado e DTOs internos (Issue #130 Bloco 3 e 4)."""

from datetime import date
import httpx
import pytest

from app.integrations.brapi_v2_client import (
    BrapiV2Client,
    BrapiV2NotFoundError,
    BrapiV2RateLimitError,
    BrapiV2TimeoutError,
    QuoteDTO,
    PriceHistoryDTO,
    CorporateEventDTO,
    DividendEventDTO,
    FIIIndicatorDTO,
    CompanyFundamentalsDTO,
)


def _mock_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_fetch_quotes_returns_typed_dtos() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/quote/PETR4,VALE3"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "PETR4",
                        "regularMarketPrice": 38.50,
                        "regularMarketChange": 0.50,
                        "regularMarketChangePercent": 1.31,
                        "currency": "BRL",
                        "marketCap": 500000000000,
                        "shortName": "PETROBRAS PN",
                    },
                    {
                        "symbol": "VALE3",
                        "regularMarketPrice": 62.10,
                        "currency": "BRL",
                    },
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example", token="test-token")
    async with _mock_client(handler) as http_client:
        quotes = await client.fetch_quotes(["PETR4", "VALE3"], client=http_client)

    assert len(quotes) == 2
    petr4 = quotes["PETR4"]
    assert isinstance(petr4, QuoteDTO)
    assert petr4.symbol == "PETR4"
    assert petr4.regular_market_price == 38.50
    assert petr4.regular_market_change == 0.50
    assert petr4.regular_market_change_percent == 1.31
    assert petr4.market_cap == 500000000000

    vale3 = quotes["VALE3"]
    assert isinstance(vale3, QuoteDTO)
    assert vale3.regular_market_price == 62.10


@pytest.mark.asyncio
async def test_fetch_history_parses_and_sorts_bars() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/quote/ITUB4"
        assert request.url.params["range"] == "1mo"
        assert request.url.params["interval"] == "1d"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "ITUB4",
                        "historicalDataPrice": [
                            {
                                "date": "2026-03-20",
                                "open": 34.0,
                                "high": 34.8,
                                "low": 33.9,
                                "close": 34.5,
                                "volume": 1200000,
                            },
                            {
                                "date": "2026-03-19",
                                "open": 33.5,
                                "high": 34.1,
                                "low": 33.4,
                                "close": 33.9,
                                "volume": 1100000,
                            },
                        ],
                    }
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example", token="test-token")
    async with _mock_client(handler) as http_client:
        history = await client.fetch_history("ITUB4", client=http_client)

    assert isinstance(history, PriceHistoryDTO)
    assert history.symbol == "ITUB4"
    assert len(history.bars) == 2
    # Verify sorted chronologically
    assert history.bars[0].bar_date == date(2026, 3, 19)
    assert history.bars[0].close == 33.9
    assert history.bars[1].bar_date == date(2026, 3, 20)
    assert history.bars[1].close == 34.5


@pytest.mark.asyncio
async def test_fetch_history_returns_none_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not found"})

    client = BrapiV2Client(base_url="https://market.example", token=None, max_retries=0)
    async with _mock_client(handler) as http_client:
        history = await client.fetch_history("UNKNOWN", client=http_client)

    assert history is None


@pytest.mark.asyncio
async def test_fetch_dividends_and_corporate_events_separation() -> None:
    """Valida o Bloco 4: separacao estrita entre proventos em dinheiro e eventos acionarios."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/quote/BBDC4"
        assert request.url.params["dividends"] == "true"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "BBDC4",
                        "dividendsData": {
                            "cashDividends": [
                                {
                                    "assetIssued": "BBDC4",
                                    "rate": 0.17,
                                    "label": "JCP",
                                    "lastDatePrior": "2026-03-05",
                                    "paymentDate": "2026-04-01",
                                    "isinCode": "BRBBDCACNPR8",
                                },
                                {
                                    "assetIssued": "BBDC4",
                                    "rate": 0.50,
                                    "label": "DIVIDENDO",
                                    "lastDatePrior": "2026-03-15",
                                    "paymentDate": "2026-04-15",
                                },
                            ],
                            "stockDividends": [
                                {
                                    "assetIssued": "BBDC4",
                                    "factor": 10.0,
                                    "label": "BONIFICACAO",
                                    "lastDatePrior": "2026-04-10",
                                    "paymentDate": "2026-04-20",
                                }
                            ],
                            "subscriptions": [
                                {
                                    "assetIssued": "BBDC4",
                                    "percentage": 5.0,
                                    "price": 14.50,
                                    "lastDatePrior": "2026-04-12",
                                    "subscriptionEndDate": "2026-05-10",
                                }
                            ],
                        },
                    }
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example", token=None)
    async with _mock_client(handler) as http_client:
        cash_divs, corp_events = await client.fetch_dividends_and_events("BBDC4", client=http_client)

    # Cash dividends
    assert len(cash_divs) == 2
    assert all(isinstance(d, DividendEventDTO) for d in cash_divs)
    assert cash_divs[0].label == "JCP"
    assert cash_divs[0].rate == 0.17
    assert cash_divs[0].last_date_prior == date(2026, 3, 5)
    assert cash_divs[0].payment_date == date(2026, 4, 1)

    assert cash_divs[1].label == "DIVIDENDO"
    assert cash_divs[1].rate == 0.50

    # Corporate events (bonificacao + subscricao)
    assert len(corp_events) == 2
    assert all(isinstance(e, CorporateEventDTO) for e in corp_events)

    bonus = [e for e in corp_events if e.event_type == "BONUS"][0]
    assert bonus.factor == 10.0
    assert bonus.last_date_prior == date(2026, 4, 10)
    assert bonus.payment_date == date(2026, 4, 20)

    rights = [e for e in corp_events if e.event_type == "RIGHTS"][0]
    assert rights.subscription_price == 14.50
    assert rights.factor == 5.0
    assert rights.subscription_end_date == date(2026, 5, 10)
    assert rights.status == "PENDING"


@pytest.mark.asyncio
async def test_fetch_fii_indicators() -> None:
    """Valida o Bloco 5: extracao de metricas de FIIs."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/quote/HGLG11"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "HGLG11",
                        "priceToBook": 1.02,
                        "dividendYield": 8.75,
                        "netWorth": 3500000000.0,
                        "shareHolders": 380000,
                        "physicalVacancy": 5.2,
                        "financialVacancy": 4.1,
                        "propertiesCount": 22,
                        "segment": "Logistica",
                    }
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example", token=None)
    async with _mock_client(handler) as http_client:
        fii = await client.fetch_fii_indicators("HGLG11", client=http_client)

    assert isinstance(fii, FIIIndicatorDTO)
    assert fii.symbol == "HGLG11"
    assert fii.pvp == 1.02
    assert fii.dividend_yield == 8.75
    assert fii.physical_vacancy == 5.2
    assert fii.financial_vacancy == 4.1
    assert fii.properties_count == 22
    assert fii.segment == "Logistica"


@pytest.mark.asyncio
async def test_fetch_company_fundamentals() -> None:
    """Valida o Bloco 6: fundamentos de acoes."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/quote/WEGE3"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "WEGE3",
                        "priceEarnings": 28.4,
                        "priceToBook": 8.1,
                        "dividendYield": 2.1,
                        "earningsPerShare": 1.85,
                        "marketCap": 210000000000.0,
                        "netRevenue": 32000000000.0,
                        "netIncome": 5400000000.0,
                        "ebitda": 7100000000.0,
                        "netMargin": 16.8,
                        "returnOnEquity": 29.5,
                        "netDebt": -1500000000.0,
                    }
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example", token=None)
    async with _mock_client(handler) as http_client:
        fund = await client.fetch_company_fundamentals("WEGE3", client=http_client)

    assert isinstance(fund, CompanyFundamentalsDTO)
    assert fund.symbol == "WEGE3"
    assert fund.pe == 28.4
    assert fund.pb == 8.1
    assert fund.eps == 1.85
    assert fund.roe == 29.5
    assert fund.ebitda == 7100000000.0


@pytest.mark.asyncio
async def test_fetch_macro_series() -> None:
    """Valida o Bloco 7: series macroeconomicas."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/prime/macro/SELIC"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"date": "2026-01-01", "value": 11.25},
                    {"date": "2026-02-01", "value": 11.25},
                ]
            },
        )

    client = BrapiV2Client(base_url="https://market.example", token=None)
    async with _mock_client(handler) as http_client:
        series = await client.fetch_macro_series("SELIC", client=http_client)

    assert len(series) == 2
    assert series[0].name == "SELIC"
    assert series[0].point_date == date(2026, 1, 1)
    assert series[0].value == 11.25


@pytest.mark.asyncio
async def test_rate_limit_error_handling() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "Too Many Requests"})

    client = BrapiV2Client(base_url="https://market.example", token=None, max_retries=0)
    async with _mock_client(handler) as http_client:
        with pytest.raises(BrapiV2RateLimitError, match="HTTP 429"):
            await client.fetch_quotes(["PETR4"], client=http_client)


@pytest.mark.asyncio
async def test_timeout_and_not_found_errors() -> None:
    def timeout_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    client = BrapiV2Client(base_url="https://market.example", token=None, max_retries=0)
    async with _mock_client(timeout_handler) as http_client:
        with pytest.raises(BrapiV2TimeoutError):
            await client._request_with_retry(http_client, "/api/quote/PETR4")

    def not_found_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "not found"})

    async with _mock_client(not_found_handler) as http_client:
        with pytest.raises(BrapiV2NotFoundError):
            await client._request_with_retry(http_client, "/api/quote/NOTFOUND")
