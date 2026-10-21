from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.portfolio import Portfolio
from app.models.portfolio_class_target import PortfolioClassTarget
from app.schemas.portfolio_analysis import (
    ConcentrationRiskLevel,
    PortfolioConsolidatedAnalysisResponse,
    RebalanceAction,
)
from app.schemas.portfolio_positions import PositionGroupResponse, PositionItemResponse
from app.services.portfolio_analysis_service import PortfolioAnalysisService


def _make_pos(
    id: int,
    ticker: str,
    asset_type: str,
    asset_label: str,
    quantity: float,
    current_value: float,
    proventos: float = 0.0,
    indexer: str | None = None,
    maturity_date: str | None = None,
) -> PositionItemResponse:
    return PositionItemResponse(
        id=id,
        ticker=ticker,
        asset_type=asset_type,
        asset_label=asset_label,
        quantity=quantity,
        average_price=10.0,
        average_price_brl=10.0,
        average_price_usd=None,
        current_price=15.0,
        current_price_brl=15.0,
        current_price_usd=None,
        current_value=current_value,
        invested_value=quantity * 10.0,
        variation_value=current_value - (quantity * 10.0),
        variation_percent=50.0,
        allocation_pct=0.0,
        logo_url=None,
        is_usd=False,
        currency="BRL",
        proventos=proventos,
        indexer=indexer,
        maturity_date=maturity_date,
    )


def _make_group(
    label: str,
    positions: list[PositionItemResponse],
    total_value: float,
    total_invested: float,
    received_dividends: float = 0.0,
    target_pct: float | None = None,
) -> PositionGroupResponse:
    return PositionGroupResponse(
        label=label,
        count=len(positions),
        total_value=total_value,
        total_invested=total_invested,
        positions=positions,
        daily_variation_value=0.0,
        daily_variation_pct=0.0,
        variation_pct=0.0,
        variation_reference_date=None,
        capital_result_value=total_value - total_invested,
        capital_result_pct=0.0,
        received_dividends=received_dividends,
        proventos_grupo=received_dividends,
        total_result_value=total_value - total_invested + received_dividends,
        total_result_pct=0.0,
        performance_source="intraday_valuation_and_received_dividends",
        proventos_as_of="2026-10-21",
        target_pct=target_pct,
    )


@pytest.mark.asyncio
async def test_portfolio_analysis_empty_portfolio() -> None:
    db = AsyncMock()
    portfolio = MagicMock(spec=Portfolio)
    portfolio.id = 1
    portfolio.user_id = 42
    portfolio.name = "Carteira Vazia"
    db.get.return_value = portfolio

    targets_result = MagicMock()
    targets_result.scalars.return_value.all.return_value = []
    db.execute.return_value = targets_result

    with patch(
        "app.services.portfolio_analysis_service.get_canonical_portfolio_positions",
        new=AsyncMock(return_value=[]),
    ):
        service = PortfolioAnalysisService(db)
        res = await service.get_portfolio_analysis(1, 42)

    assert isinstance(res, PortfolioConsolidatedAnalysisResponse)
    assert res.portfolio_id == 1
    assert res.total_value == 0.0
    assert res.classes_analyzed_count == 0
    assert res.classes == []
    assert "valuation" in res.provenance
    assert "targets" in res.provenance


@pytest.mark.asyncio
async def test_portfolio_analysis_rebalance_and_concentration() -> None:
    db = AsyncMock()
    portfolio = MagicMock(spec=Portfolio)
    portfolio.id = 15
    portfolio.user_id = 99
    portfolio.name = "Carteira Principal"
    db.get.return_value = portfolio

    # Targets: Ações 50%, FIIs 30%, Renda Fixa 20%
    t_acoes = MagicMock(spec=PortfolioClassTarget, asset_type="ACAO", target_pct=50.0)
    t_fiis = MagicMock(spec=PortfolioClassTarget, asset_type="FII", target_pct=30.0)
    t_rf = MagicMock(spec=PortfolioClassTarget, asset_type="RENDA_FIXA", target_pct=20.0)
    targets_result = MagicMock()
    targets_result.scalars.return_value.all.return_value = [t_acoes, t_fiis, t_rf]
    db.execute.return_value = targets_result

    # Groups:
    # Ações: R$ 20.000 (PETR4 R$ 15.000, VALE3 R$ 5.000) -> 20.000 / 100.000 = 20% (Target 50% -> BUY gap R$ 30.000)
    pos_petr = _make_pos(1, "PETR4", "ACAO", "Petrobras", 500, 15000.0, proventos=1200.0)
    pos_vale = _make_pos(2, "VALE3", "ACAO", "Vale", 100, 5000.0, proventos=300.0)
    group_acoes = _make_group(
        label="Ações",
        positions=[pos_petr, pos_vale],
        total_value=20000.0,
        total_invested=15000.0,
        received_dividends=1500.0,
        target_pct=50.0,
    )

    # FIIs: R$ 40.000 (HGLG11 R$ 20.000, MXRF11 R$ 20.000) -> 40.000 / 100.000 = 40% (Target 30% -> REDUCE excess R$ 10.000)
    pos_hglg = _make_pos(3, "HGLG11", "FII", "CSHG Logística", 100, 20000.0, proventos=1800.0)
    pos_mxrf = _make_pos(4, "MXRF11", "FII", "Maxi Renda", 2000, 20000.0, proventos=2200.0)
    group_fiis = _make_group(
        label="FIIs",
        positions=[pos_hglg, pos_mxrf],
        total_value=40000.0,
        total_invested=38000.0,
        received_dividends=4000.0,
        target_pct=30.0,
    )

    # Renda Fixa: R$ 40.000 (CDB CDI R$ 30.000, Tesouro IPCA R$ 10.000) -> 40% (Target 20% -> REDUCE)
    pos_cdb = _make_pos(5, "CDB_BANCO", "RENDA_FIXA", "CDB 110% CDI", 30, 30000.0, indexer="CDI")
    pos_ntnb = _make_pos(6, "TESOURO_IPCA", "TESOURO_DIRETO", "Tesouro IPCA+ 2029", 10, 10000.0, indexer="IPCA")
    group_rf = _make_group(
        label="Renda Fixa",
        positions=[pos_cdb, pos_ntnb],
        total_value=40000.0,
        total_invested=40000.0,
        received_dividends=0.0,
        target_pct=20.0,
    )

    with patch(
        "app.services.portfolio_analysis_service.get_canonical_portfolio_positions",
        new=AsyncMock(return_value=[group_acoes, group_fiis, group_rf]),
    ):
        service = PortfolioAnalysisService(db)
        res = await service.get_portfolio_analysis(15, 99)

    assert res.total_value == 100000.0
    assert res.classes_analyzed_count == 3

    # Ações checks
    acoes_analysis = next(c for c in res.classes if c.asset_type == "ACAO")
    assert acoes_analysis.allocation.current_weight_pct == 20.0
    assert acoes_analysis.allocation.target_weight_pct == 50.0
    assert acoes_analysis.allocation.rebalance_action == RebalanceAction.BUY
    assert acoes_analysis.allocation.gap_value == 30000.0
    assert acoes_analysis.concentration.top_asset.ticker == "PETR4"
    assert acoes_analysis.concentration.top_asset.weight_in_class_pct == 75.0
    assert acoes_analysis.concentration.risk_level == ConcentrationRiskLevel.CRITICAL
    assert acoes_analysis.income.is_applicable is True
    assert acoes_analysis.income.total_proventos == 1500.0
    assert acoes_analysis.income.top_income_asset == "PETR4"

    # FIIs checks
    fiis_analysis = next(c for c in res.classes if c.asset_type == "FII")
    assert fiis_analysis.allocation.current_weight_pct == 40.0
    assert fiis_analysis.allocation.target_weight_pct == 30.0
    assert fiis_analysis.allocation.rebalance_action == RebalanceAction.REDUCE
    assert fiis_analysis.concentration.risk_level == ConcentrationRiskLevel.WARNING

    # Renda Fixa checks
    rf_analysis = next(c for c in res.classes if "RENDA_FIXA" in c.asset_type)
    assert rf_analysis.fixed_income.is_applicable is True
    assert rf_analysis.fixed_income.cdi_allocation_pct == 75.0
    assert rf_analysis.fixed_income.ipca_allocation_pct == 25.0

    # Consolidated checks
    assert "Ações" in res.rebalance_priority_classes
    assert res.max_divergence_class == "Ações"
    assert 0 <= res.overall_health_score <= 100


@pytest.mark.asyncio
async def test_portfolio_analysis_unauthorized() -> None:
    db = AsyncMock()
    portfolio = MagicMock(spec=Portfolio)
    portfolio.id = 1
    portfolio.user_id = 99
    db.get.return_value = portfolio

    service = PortfolioAnalysisService(db)
    with pytest.raises(ValueError, match="não autorizado"):
        await service.get_portfolio_analysis(1, 100)
