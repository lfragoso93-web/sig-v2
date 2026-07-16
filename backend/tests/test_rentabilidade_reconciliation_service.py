from unittest.mock import AsyncMock, patch

import pytest

from app.services.rentabilidade_reconciliation_service import reconcile_rentabilidade_page


@pytest.mark.asyncio
async def test_reconciliation_matches_summary_and_class_totals():
    summary = {
        "total_patrimonio": 1500.0,
        "total_investido": 1200.0,
        "ganho_nao_realizado": 200.0,
        "ganho_realizado": 50.0,
        "lucro_total": 300.0,
        "total_proventos": 50.0,
    }
    kpis = {
        "patrimonio_atual": 1500.0,
        "custo_posicoes_abertas": 1200.0,
        "resultado_nao_realizado": 200.0,
        "resultado_realizado": 50.0,
        "resultado_total": 300.0,
        "proventos_total": 50.0,
        "performance_as_of": "2026-07-15",
    }
    classes = [
        {
            "asset_type": "ACAO",
            "current_value": 1000.0,
            "cost_basis": 800.0,
            "dedicated_history_required": False,
            "twr_available": True,
        },
        {
            "asset_type": "RENDA_FIXA",
            "current_value": 500.0,
            "cost_basis": 400.0,
            "dedicated_history_required": True,
            "twr_available": False,
        },
    ]

    with patch(
        "app.services.rentabilidade_reconciliation_service.get_canonical_portfolio_summary",
        AsyncMock(return_value=summary),
    ), patch(
        "app.services.rentabilidade_reconciliation_service.get_rentabilidade_kpis",
        AsyncMock(return_value=kpis),
    ), patch(
        "app.services.rentabilidade_reconciliation_service.get_canonical_class_performance",
        AsyncMock(return_value=classes),
    ):
        result = await reconcile_rentabilidade_page(AsyncMock(), 1, 2)

    assert result["is_reconciled"] is True
    assert result["classes"]["patrimonio"]["difference"] == 0.0
    assert result["unsupported_class_twr"] == ["RENDA_FIXA"]
    assert result["twr_comparability_status"] == "partial_by_design"


@pytest.mark.asyncio
async def test_reconciliation_surfaces_monetary_difference():
    summary = {
        "total_patrimonio": 1000.0,
        "total_investido": 900.0,
        "ganho_nao_realizado": 100.0,
        "ganho_realizado": 0.0,
        "lucro_total": 100.0,
        "total_proventos": 0.0,
    }
    kpis = {
        "patrimonio_atual": 999.0,
        "custo_posicoes_abertas": 900.0,
        "resultado_nao_realizado": 100.0,
        "resultado_realizado": 0.0,
        "resultado_total": 100.0,
        "proventos_total": 0.0,
        "performance_as_of": None,
    }

    with patch(
        "app.services.rentabilidade_reconciliation_service.get_canonical_portfolio_summary",
        AsyncMock(return_value=summary),
    ), patch(
        "app.services.rentabilidade_reconciliation_service.get_rentabilidade_kpis",
        AsyncMock(return_value=kpis),
    ), patch(
        "app.services.rentabilidade_reconciliation_service.get_canonical_class_performance",
        AsyncMock(return_value=[{"asset_type": "ACAO", "current_value": 1000.0, "cost_basis": 900.0, "dedicated_history_required": False, "twr_available": True}]),
    ):
        result = await reconcile_rentabilidade_page(AsyncMock(), 1, 2)

    assert result["is_reconciled"] is False
    assert result["monetary"]["patrimonio"]["difference"] == -1.0
