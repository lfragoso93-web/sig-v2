"""Testes para o servico de enriquecimento de FIIs, acoes e macroeconomia (Issue #130 Blocos 5, 6, 7)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.integrations.brapi_v2_client import (
    CompanyFundamentalsDTO,
    FIIIndicatorDTO,
    MacroSeriesPointDTO,
)
from app.services.asset_coverage_service import AssetCoverageService
from app.services.asset_enrichment_service import AssetEnrichmentService


@pytest.fixture
def mock_v2_client():
    client = MagicMock()
    client.fetch_fii_indicators = AsyncMock()
    client.fetch_company_fundamentals = AsyncMock()
    client.fetch_macro_series = AsyncMock()
    client.fetch_dividends_and_events = AsyncMock(return_value=([], []))
    return client


@pytest.fixture
def coverage_service():
    return AssetCoverageService()


@pytest.fixture
def enrichment_service(mock_v2_client):
    return AssetEnrichmentService(client=mock_v2_client)


@pytest.mark.asyncio
async def test_get_fii_indicators_success_and_cache(enrichment_service, mock_v2_client) -> None:
    expected_dto = FIIIndicatorDTO(
        symbol="KNRI11",
        pvp=0.98,
        dividend_yield=9.1,
        net_worth=3800000000.0,
        share_holders=250000,
        physical_vacancy=4.2,
        financial_vacancy=3.5,
        properties_count=21,
        segment="Hibrido",
    )
    mock_v2_client.fetch_fii_indicators.return_value = expected_dto

    # Primeira chamada: consulta cliente e salva em cache
    result = await enrichment_service.get_fii_indicators("KNRI11")
    assert result == expected_dto
    assert mock_v2_client.fetch_fii_indicators.call_count == 1

    # Segunda chamada: deve vir do cache sem chamar o cliente
    cached_result = await enrichment_service.get_fii_indicators("KNRI11")
    assert cached_result.symbol == "KNRI11"
    assert cached_result.pvp == 0.98
    assert cached_result.properties_count == 21
    assert mock_v2_client.fetch_fii_indicators.call_count == 1


@pytest.mark.asyncio
async def test_get_stock_fundamentals_success_and_cache(enrichment_service, mock_v2_client) -> None:
    expected_dto = CompanyFundamentalsDTO(
        symbol="ITUB4",
        pe=8.5,
        pb=1.4,
        dividend_yield=6.8,
        eps=3.95,
        market_cap=310000000000.0,
        net_revenue=150000000000.0,
        net_income=35000000000.0,
        ebitda=45000000000.0,
        net_margin=23.3,
        roe=21.5,
        net_debt=0.0,
    )
    mock_v2_client.fetch_company_fundamentals.return_value = expected_dto

    result = await enrichment_service.get_stock_fundamentals("ITUB4")
    assert result == expected_dto
    assert mock_v2_client.fetch_company_fundamentals.call_count == 1

    # Segunda chamada do cache
    cached = await enrichment_service.get_stock_fundamentals("ITUB4")
    assert cached.symbol == "ITUB4"
    assert cached.pe == 8.5
    assert cached.roe == 21.5
    assert mock_v2_client.fetch_company_fundamentals.call_count == 1


@pytest.mark.asyncio
async def test_get_macro_series_success(enrichment_service, mock_v2_client) -> None:
    expected_points = [
        MacroSeriesPointDTO(name="SELIC", point_date=date(2026, 1, 1), value=11.25),
        MacroSeriesPointDTO(name="SELIC", point_date=date(2026, 2, 1), value=11.25),
    ]
    mock_v2_client.fetch_macro_series.return_value = expected_points

    result = await enrichment_service.get_macro_series("SELIC")
    assert len(result) == 2
    assert result[0].point_date == date(2026, 1, 1)
    assert result[0].value == 11.25

    # Segunda chamada do cache
    cached = await enrichment_service.get_macro_series("SELIC")
    assert len(cached) == 2
    assert mock_v2_client.fetch_macro_series.call_count == 1


@pytest.mark.asyncio
async def test_get_asset_enrichment_unifies_report(enrichment_service, mock_v2_client) -> None:
    fii_dto = FIIIndicatorDTO(
        symbol="XPML11",
        pvp=1.01,
        dividend_yield=8.5,
        properties_count=18,
    )
    mock_v2_client.fetch_fii_indicators.return_value = fii_dto

    enrichment = await enrichment_service.get_asset_enrichment("XPML11", asset_type="FII")
    assert enrichment["ticker"] == "XPML11"
    assert enrichment["fii_indicators"] is not None
    assert enrichment["fii_indicators"]["pvp"] == 1.01
    assert enrichment["fii_indicators"]["properties_count"] == 18
    assert enrichment["stock_fundamentals"] is None



@pytest.mark.asyncio
async def test_get_asset_enrichment_crypto(enrichment_service) -> None:
    from unittest.mock import patch
    crypto_payload = {
        "coin": "BTC",
        "coin_name": "Bitcoin",
        "price_brl": 385000.0,
        "price_usd": 65000.0,
        "market_cap_rank": 1,
    }
    with patch("app.services.asset_enrichment_service.fetch_crypto_quote_and_metrics", return_value=crypto_payload):
        enrichment = await enrichment_service.get_asset_enrichment("BTC", asset_type="CRIPTO")
        assert enrichment["ticker"] == "BTC"
        assert enrichment["crypto_indicators"] is not None
        assert enrichment["crypto_indicators"]["price_brl"] == 385000.0
        assert enrichment["crypto_indicators"]["market_cap_rank"] == 1


@pytest.mark.asyncio
async def test_get_asset_enrichment_treasury(enrichment_service) -> None:
    from unittest.mock import patch
    treasury_payload = {
        "symbol": "tesouro-ipca-2035",
        "bond_type": "Tesouro IPCA+",
        "name": "Tesouro IPCA+ 2035",
        "indexer": "IPCA",
        "buy_rate": 6.25,
        "buy_price": 2450.50,
    }
    with patch("app.services.asset_enrichment_service.fetch_treasury_bond_detail", return_value=treasury_payload):
        enrichment = await enrichment_service.get_asset_enrichment("tesouro-ipca-2035", asset_type="TESOURO_DIRETO")
        assert enrichment["ticker"] == "TESOURO-IPCA-2035"
        assert enrichment["treasury_indicators"] is not None
        assert enrichment["treasury_indicators"]["indexer"] == "IPCA"
        assert enrichment["treasury_indicators"]["buy_rate"] == 6.25


@pytest.mark.asyncio
async def test_get_asset_enrichment_international(enrichment_service) -> None:
    from unittest.mock import patch
    finnhub_payload = {
        "profile": {
            "country": "US",
            "currency": "USD",
            "exchange": "NASDAQ",
            "industry": "Technology",
            "name": "Apple Inc",
            "logo": "https://logo.png",
            "market_cap": 3000000000000.0,
            "weburl": "https://apple.com",
        },
        "metrics": {
            "pe": 32.5,
            "pb": 45.0,
            "dividend_yield": 0.55,
            "roe": 140.0,
            "net_margin": 26.5,
            "eps": 6.8,
            "beta": 1.1,
        },
        "recommendations": {
            "strong_buy": 10,
            "buy": 20,
            "hold": 8,
            "sell": 1,
            "strong_sell": 0,
            "consensus": "STRONG_BUY",
        },
    }
    with patch("app.services.asset_enrichment_service.fetch_finnhub_enrichment", return_value=finnhub_payload):
        enrichment = await enrichment_service.get_asset_enrichment("AAPL", asset_type="STOCK")
        assert enrichment["ticker"] == "AAPL"
        assert enrichment["stock_fundamentals"] is not None
        assert enrichment["stock_fundamentals"]["pe"] == 32.5
        assert enrichment["stock_fundamentals"]["sector"] == "Technology"
        assert enrichment["international_profile"] is not None
        assert enrichment["international_profile"]["country"] == "US"
        assert enrichment["international_profile"]["consensus"] == "STRONG_BUY"


@pytest.mark.asyncio
async def test_get_asset_enrichment_etf(enrichment_service) -> None:
    # BOVA11 deve ser enriquecido como ETF, sem fundamentos corporativos de ações (sem P/L ou P/VP de empresa)
    enrichment = await enrichment_service.get_asset_enrichment("BOVA11", asset_type="ETF_NACIONAL")
    assert enrichment["ticker"] == "BOVA11"
    assert enrichment["asset_class"] == "ETF"
    assert enrichment["stock_fundamentals"] is None
    assert enrichment["etf_indicators"] is not None
    assert enrichment["etf_indicators"]["benchmark"] == "Índice Bovespa (IBOV)"
    assert enrichment["etf_indicators"]["expense_ratio"] == 0.10
    assert "BlackRock" in enrichment["etf_indicators"]["manager"]
    assert enrichment["etf_indicators"]["dividend_policy"] == "Reinvestimento Automático de Proventos"


@pytest.mark.asyncio
async def test_get_asset_enrichment_bdr(enrichment_service) -> None:
    enrichment = await enrichment_service.get_asset_enrichment("AAPL34", asset_type="BDR")
    assert enrichment["ticker"] == "AAPL34"
    assert enrichment["asset_class"] == "BDR"
    assert enrichment["bdr_indicators"] is not None
    assert enrichment["bdr_indicators"]["underlying_ticker"] == "AAPL"
    assert enrichment["bdr_indicators"]["underlying_company"] == "Apple Inc."
    assert "B3" in enrichment["bdr_indicators"]["depositary_bank"]


@pytest.mark.asyncio
async def test_get_dividend_history_with_provider_fallback(enrichment_service, mock_v2_client) -> None:
    from app.integrations.brapi_v2_client import DividendEventDTO
    div_dto = DividendEventDTO(
        symbol="PETR4",
        label="DIVIDENDO",
        rate=1.25,
        last_date_prior=date(2026, 4, 15),
        payment_date=date(2026, 5, 20),
    )
    mock_v2_client.fetch_dividends_and_events.return_value = ([div_dto], [])

    history, metrics = await enrichment_service.get_dividend_history("PETR4")
    assert len(history) == 1
    assert history[0]["type"] == "DIVIDENDO"
    assert history[0]["value"] == 1.25
    assert history[0]["payment_date"] == "2026-05-20"
    assert metrics is not None
    assert metrics["total_paid_12m"] == 1.25
    assert metrics["payments_count_12m"] == 1
