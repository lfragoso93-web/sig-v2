from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.asset_ai_analysis_service import asset_ai_analysis_service
from app.services.asset_reports_and_news_service import (
    AssetReportsAndNewsService,
    _parse_br_or_iso_date,
)


def test_parse_br_or_iso_date():
    assert _parse_br_or_iso_date("15/10/2026 18:30") == "2026-10-15"
    assert _parse_br_or_iso_date("10/2026") == "2026-10-01"
    assert _parse_br_or_iso_date("2026-11-03") == "2026-11-03"


@pytest.mark.asyncio
async def test_fii_reports_parses_fnet_payload():
    service = AssetReportsAndNewsService()
    fake_fnet_payload = {
        "data": [
            {
                "id": 987654,
                "categoriaDocumento": "Relatórios",
                "tipoDocumento": "Relatório Gerencial",
                "dataReferencia": "10/2026",
                "dataEntrega": "05/11/2026 14:22",
                "descricaoStatus": "Ativo",
                "versao": 1,
                "descricaoFundo": "MAXI RENDA FII",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_fnet_payload

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.asset_reports_and_news_service.httpx.AsyncClient", return_value=mock_client):
        reports = await service.fetch_fii_reports(
            "MXRF11",
            enrichment={"fii_indicators": {"cnpj": "97.521.225/0001-25"}},
        )

    assert len(reports) == 1
    assert reports[0]["id"] == "987654"
    assert reports[0]["title"] == "Relatório Gerencial"
    assert reports[0]["is_management_report"] is True
    assert "exibirDocumento?id=987654" in reports[0]["url"]


@pytest.mark.asyncio
async def test_asset_ai_analysis_confronts_fii_report_and_metrics():
    result = await asset_ai_analysis_service.analyze_asset(
        asset={"ticker": "MXRF11", "name": "Maxi Renda FII", "asset_type": "FII", "currency": "BRL", "last_price": 9.85},
        enrichment={
            "fii_indicators": {
                "pvp": 0.96,
                "nav_per_share": 10.26,
                "dividend_yield": 11.4,
                "physical_vacancy": 1.5,
                "financial_vacancy": 1.2,
                "properties_count": 12,
                "segment": "Híbrido / Papel",
            },
            "dividend_metrics": {
                "payments_count_12m": 12,
                "total_paid_12m": 1.12,
                "frequency": "Mensal",
                "dy_12m": 11.4,
            },
        },
        price_history=[
            {"timestamp": "2026-09-01", "close": 9.50},
            {"timestamp": "2026-10-01", "close": 9.70},
            {"timestamp": "2026-11-01", "close": 9.85},
        ],
        dividends=[{"ex_date": "2026-10-30", "value_per_unit": 0.09, "type": "RENDIMENTO"}],
        reports=[
            {
                "id": "987654",
                "title": "Relatório Gerencial",
                "reference_date": "2026-10-01",
                "delivery_date": "2026-11-05",
                "url": "https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=987654&cvm=true",
                "is_management_report": True,
            }
        ],
        latest_report_excerpt={
            "document_id": "987654",
            "title": "Relatório Gerencial",
            "reference_date": "2026-10-01",
            "delivery_date": "2026-11-05",
            "pages_count": 18,
            "url": "https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id=987654&cvm=true",
            "excerpt": "No mês de outubro o resultado do fundo manteve-se sólido com vacância controlada e distribuição de rendimentos recorrente.",
        },
        news=[{"title": "MXRF11 anuncia novos dividendos para novembro", "source": "InfoMoney", "url": "https://example.com"}],
    )

    assert result["ticker"] == "MXRF11"
    assert result["score"] >= 75
    assert len(result["strengths"]) >= 2
    assert any("Relatório Gerencial oficial" in c for c in result["report_confrontation"])
    assert any("Noticiário recente" in c for c in result["report_confrontation"])
    assert result["latest_report_referenced"]["url"].startswith("https://fnet.bmfbovespa.com.br")


@pytest.mark.asyncio
async def test_asset_ai_analysis_handles_reports_without_excerpt_and_filters_trailing_12m_dividends():
    result = await asset_ai_analysis_service.analyze_asset(
        asset={"ticker": "PETR4", "name": "Petrobras", "asset_type": "ACAO", "currency": "BRL", "last_price": 38.0},
        enrichment={"stock_fundamentals": {"pe": 5.5, "pb": 1.2, "roe": 22.0}},
        price_history=[{"timestamp": "2026-11-01", "close": 38.0}],
        dividends=[
            {"ex_date": "2026-10-01", "value_per_unit": 1.0, "type": "DIVIDENDO"},
            {"ex_date": "2023-05-01", "value_per_unit": 5.0, "type": "DIVIDENDO"},
        ],
        reports=[
            {
                "id": "9512-itr-2026",
                "title": "ITR — Informações Trimestrais",
                "reference_date": "2026-09-30",
                "delivery_date": "2026-11-01",
                "url": "https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx",
                "is_management_report": True,
            }
        ],
        latest_report_excerpt=None,
        news=[],
    )
    assert result["latest_report_referenced"]["title"] == "ITR — Informações Trimestrais"
    assert result["dividend_outlook"]["payments_count_12m"] == 1
    assert result["dividend_outlook"]["total_paid_12m"] == 1.0
