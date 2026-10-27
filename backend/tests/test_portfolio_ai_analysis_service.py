from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.schemas.portfolio_analysis import (
    ClassAllocationAnalysis,
    ClassAnalysisDetail,
    ClassConcentrationAnalysis,
    ClassFixedIncomeAnalysis,
    ClassIncomeAnalysis,
    ConcentrationRiskLevel,
    PortfolioConsolidatedAnalysisResponse,
    RebalanceAction,
    TopAssetConcentration,
)
from unittest.mock import patch, MagicMock
from app.services.portfolio_ai_analysis_service import (
    DeterministicAuditExplainer,
    PortfolioAiAnalysisService,
)


def _make_mock_analysis_dto() -> PortfolioConsolidatedAnalysisResponse:
    return PortfolioConsolidatedAnalysisResponse(
        portfolio_id=1,
        portfolio_name="Carteira Teste Governança",
        reference_date="2026-10-21",
        total_value=100000.0,
        overall_health_score=85,
        max_divergence_class="Ações",
        classes_analyzed_count=3,
        rebalance_priority_classes=["Ações"],
        classes=[
            ClassAnalysisDetail(
                asset_type="acoes",
                label="Ações",
                health_score=75,
                allocation=ClassAllocationAnalysis(
                    current_value=30000.0,
                    current_weight_pct=30.0,
                    target_weight_pct=40.0,
                    target_value=40000.0,
                    gap_weight_pct=-10.0,
                    gap_value=-10000.0,
                    rebalance_action=RebalanceAction.BUY,
                    suggested_action_label="Aportar",
                ),
                concentration=ClassConcentrationAnalysis(
                    asset_count=2,
                    top_asset=TopAssetConcentration(
                        ticker="PETR4",
                        name="Petrobras PN",
                        current_value=20000.0,
                        weight_in_class_pct=66.7,
                        weight_in_portfolio_pct=20.0,
                    ),
                    hhi_score=0.55,
                    risk_level=ConcentrationRiskLevel.WARNING,
                    risk_label="Atenção",
                    status_message="Concentração acima do limiar recomendado",
                ),
                income=ClassIncomeAnalysis(
                    is_applicable=True,
                    total_proventos=1200.0,
                    weighted_dy_pct=6.0,
                    top_income_asset="PETR4",
                    status_label="Geração ativa",
                ),
                fixed_income=ClassFixedIncomeAnalysis(is_applicable=False),
                key_findings=["Subalocação de 10%"],
            ),
            ClassAnalysisDetail(
                asset_type="renda_fixa",
                label="Renda Fixa",
                health_score=90,
                allocation=ClassAllocationAnalysis(
                    current_value=45000.0,
                    current_weight_pct=45.0,
                    target_weight_pct=40.0,
                    target_value=40000.0,
                    gap_weight_pct=5.0,
                    gap_value=5000.0,
                    rebalance_action=RebalanceAction.HOLD,
                    suggested_action_label="Aguardar",
                ),
                concentration=ClassConcentrationAnalysis(
                    asset_count=3,
                    top_asset=TopAssetConcentration(
                        ticker="CDB DI",
                        current_value=25000.0,
                        weight_in_class_pct=55.5,
                        weight_in_portfolio_pct=25.0,
                    ),
                    risk_level=ConcentrationRiskLevel.BALANCED,
                    risk_label="Equilibrado",
                    status_message="Distribuição equilibrada",
                ),
                income=ClassIncomeAnalysis(
                    is_applicable=False,
                    total_proventos=0.0,
                    status_label="Não aplicável",
                ),
                fixed_income=ClassFixedIncomeAnalysis(
                    is_applicable=True,
                    cdi_allocation_pct=70.0,
                    ipca_allocation_pct=30.0,
                    pre_allocation_pct=0.0,
                    maturing_next_12m_value=10000.0,
                    maturing_next_12m_pct=22.2,
                ),
                key_findings=["Alinhado com a meta"],
            ),
            ClassAnalysisDetail(
                asset_type="fiis",
                label="Fundos Imobiliários",
                health_score=95,
                allocation=ClassAllocationAnalysis(
                    current_value=25000.0,
                    current_weight_pct=25.0,
                    target_weight_pct=20.0,
                    target_value=20000.0,
                    gap_weight_pct=5.0,
                    gap_value=5000.0,
                    rebalance_action=RebalanceAction.HOLD,
                    suggested_action_label="Aguardar",
                ),
                concentration=ClassConcentrationAnalysis(
                    asset_count=5,
                    top_asset=TopAssetConcentration(
                        ticker="HGLG11",
                        current_value=7000.0,
                        weight_in_class_pct=28.0,
                        weight_in_portfolio_pct=7.0,
                    ),
                    risk_level=ConcentrationRiskLevel.LOW,
                    risk_label="Baixo Risco",
                    status_message="Excelente diversificação",
                ),
                income=ClassIncomeAnalysis(
                    is_applicable=True,
                    total_proventos=2100.0,
                    weighted_dy_pct=9.2,
                    top_income_asset="HGLG11",
                    status_label="Geração expressiva",
                ),
                fixed_income=ClassFixedIncomeAnalysis(is_applicable=False),
                key_findings=["Fluxo recorrente consistente"],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_deterministic_explainer_generates_grounded_analysis():
    explainer = DeterministicAuditExplainer()
    mock_dto = _make_mock_analysis_dto()

    res = await explainer.explain_analysis(mock_dto)

    assert res.portfolio_id == 1
    assert res.overall_health_score == 85
    assert "Ações" in res.rebalancing_strategy or "aportes" in res.rebalancing_strategy
    assert len(res.key_strengths) >= 2
    assert len(res.attention_points) >= 1
    assert any("PETR4" in pt or "Ações" in pt for pt in res.attention_points)
    assert res.metadata.is_mock_or_deterministic is True
    assert "não constitui recomendação" in res.metadata.disclaimer.lower()


@pytest.mark.asyncio
async def test_portfolio_ai_analysis_service_orchestration():
    mock_db = AsyncMock()
    service = PortfolioAiAnalysisService(mock_db)
    service.analysis_service.get_portfolio_analysis = AsyncMock(return_value=_make_mock_analysis_dto())

    res = await service.get_ai_analysis(portfolio_id=1, user_id=10)

    assert res.portfolio_id == 1
    assert res.overall_health_score == 85
    assert len(res.contribution_scenarios) == 3
    assert res.metadata.provider == "sgi-audit-explainer-v1"


@pytest.mark.asyncio
@patch("app.services.portfolio_ai_analysis_service.get_canonical_portfolio_positions")
async def test_simulate_contribution_prioritizes_deficit_class(mock_get_positions):
    mock_get_positions.return_value = MagicMock(groups=[])
    mock_db = AsyncMock()
    service = PortfolioAiAnalysisService(mock_db)
    service.analysis_service.get_portfolio_analysis = AsyncMock(return_value=_make_mock_analysis_dto())

    sim = await service.simulate_contribution(portfolio_id=1, user_id=10, amount=5000.0)

    assert sim.portfolio_id == 1
    assert sim.contribution_amount == 5000.0
    assert sim.projected_total_value == 105000.0
    
    # Ações é a única classe com déficit (target 40% de 105.000 = 42.000, atual 30.000 -> déficit 12.000)
    acoes_alloc = next(a for a in sim.suggested_allocations if a.asset_type == "acoes")
    assert acoes_alloc.allocated_amount == 5000.0
    assert acoes_alloc.projected_value == 35000.0
    assert "Ações" in sim.overall_impact_summary


@pytest.mark.asyncio
async def test_ai_qa_answers_grounded_in_metrics():
    mock_db = AsyncMock()
    service = PortfolioAiAnalysisService(mock_db)
    service.analysis_service.get_portfolio_analysis = AsyncMock(return_value=_make_mock_analysis_dto())

    # Pergunta sobre score
    ans_score = await service.answer_ai_question(portfolio_id=1, user_id=10, question="Qual meu score de alocação?")
    assert "85/100" in ans_score.answer
    assert "overall_health_score" in ans_score.key_metrics_referenced

    # Pergunta sobre concentração
    ans_conc = await service.answer_ai_question(portfolio_id=1, user_id=10, question="Onde tenho risco de concentração?")
    assert "PETR4" in ans_conc.answer or "Ações" in ans_conc.answer
    assert "top_asset" in ans_conc.key_metrics_referenced

    # Pergunta sobre aporte
    ans_aporte = await service.answer_ai_question(portfolio_id=1, user_id=10, question="Onde devo realizar meu próximo aporte?")
    assert "Ações" in ans_aporte.answer


@pytest.mark.asyncio
@patch("app.services.portfolio_ai_analysis_service.get_canonical_portfolio_positions")
async def test_simulate_contribution_strategies_and_asset_recommendations(mock_get_positions):
    # Simular posições abertas na classe Ações
    pos_petr = MagicMock(
        ticker="PETR4",
        asset_label="Petrobras",
        quantity=100.0,
        current_price=30.0,
        current_price_brl=30.0,
        current_value=3000.0,
        received_dividends=500.0,
        variation_pct=15.0,
        capital_result_value=400.0,
    )
    pos_vale = MagicMock(
        ticker="VALE3",
        asset_label="Vale",
        quantity=50.0,
        current_price=60.0,
        current_price_brl=60.0,
        current_value=3000.0,
        received_dividends=200.0,
        variation_pct=5.0,
        capital_result_value=150.0,
    )
    group_acoes = MagicMock(
        label="Ações",
        positions=[pos_petr, pos_vale],
    )
    group_acoes.positions[0].asset_type = "ACAO"
    mock_get_positions.return_value = MagicMock(groups=[group_acoes])
    mock_db = AsyncMock()
    service = PortfolioAiAnalysisService(mock_db)
    service.analysis_service.get_portfolio_analysis = AsyncMock(return_value=_make_mock_analysis_dto())

    # 1. Estratégia Proventos
    sim_prov = await service.simulate_contribution(
        portfolio_id=1, user_id=10, amount=5000.0, strategy="proventos"
    )
    assert sim_prov.strategy == "proventos"
    assert len(sim_prov.suggested_assets) > 0
    assert any("Proventos" in a.reason for a in sim_prov.suggested_assets)
    assert sum(a.suggested_amount for a in sim_prov.suggested_assets) == pytest.approx(5000.0)

    # 2. Estratégia Performance
    sim_perf = await service.simulate_contribution(
        portfolio_id=1, user_id=10, amount=5000.0, strategy="performance"
    )
    assert sim_perf.strategy == "performance"
    assert len(sim_perf.suggested_assets) > 0
    assert any("Performance" in a.reason for a in sim_perf.suggested_assets)
    assert sum(a.suggested_amount for a in sim_perf.suggested_assets) == pytest.approx(5000.0)

    # 3. Estratégia Patrimônio
    sim_patr = await service.simulate_contribution(
        portfolio_id=1, user_id=10, amount=5000.0, strategy="patrimonio"
    )
    assert sim_patr.strategy == "patrimonio"
    assert len(sim_patr.suggested_assets) > 0
    assert any("Patrimônio" in a.reason for a in sim_patr.suggested_assets)
    assert sum(a.suggested_amount for a in sim_patr.suggested_assets) == pytest.approx(5000.0)


@pytest.mark.asyncio
async def test_simulate_contribution_empty_portfolio_with_and_without_targets():
    mock_db = AsyncMock()
    service = PortfolioAiAnalysisService(mock_db)

    # Sem classes/metas
    empty_dto = PortfolioConsolidatedAnalysisResponse(
        portfolio_id=2,
        portfolio_name="Carteira Vazia",
        reference_date="2026-10-21",
        total_value=0.0,
        overall_health_score=70,
        max_divergence_class=None,
        classes_analyzed_count=0,
        rebalance_priority_classes=[],
        classes=[],
    )
    service.analysis_service.get_portfolio_analysis = AsyncMock(return_value=empty_dto)

    sim_empty = await service.simulate_contribution(portfolio_id=2, user_id=10, amount=2000.0)
    assert sim_empty.current_total_value == 0.0
    assert len(sim_empty.suggested_allocations) == 0
    assert len(sim_empty.suggested_assets) == 0
    assert "Configure as metas" in sim_empty.overall_impact_summary
