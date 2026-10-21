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
