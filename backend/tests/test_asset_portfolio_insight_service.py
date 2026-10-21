"""Testes para o servico de correlacao de ativos com a carteira e insights de IA (Issue #58)."""

from unittest.mock import AsyncMock, patch
import pytest

from app.services.asset_portfolio_insight_service import (
    AssetPortfolioInsightService,
)


@pytest.fixture
def insight_service():
    return AssetPortfolioInsightService()


@pytest.mark.asyncio
async def test_get_insight_for_held_asset(insight_service) -> None:
    mock_db = AsyncMock()

    mock_groups = [
        {
            "asset_type": "ACAO",
            "label": "Ações",
            "total_value": 40000.0,
            "total_invested": 30000.0,
            "positions": [
                {
                    "ticker": "PETR4",
                    "asset_type": "ACAO",
                    "quantity": 500,
                    "average_price": 30.0,
                    "invested_value": 15000.0,
                    "current_price": 40.0,
                    "current_value": 20000.0,
                    "proventos": 2000.0,
                },
                {
                    "ticker": "VALE3",
                    "asset_type": "ACAO",
                    "quantity": 300,
                    "average_price": 60.0,
                    "invested_value": 18000.0,
                    "current_price": 66.67,
                    "current_value": 20000.0,
                    "proventos": 1000.0,
                },
            ],
        },
        {
            "asset_type": "FII",
            "label": "FIIs",
            "total_value": 60000.0,
            "total_invested": 55000.0,
            "positions": [],
        },
    ]

    mock_targets = {"ACAO": 30.0, "FII": 70.0}

    mock_enrichment = {
        "ticker": "PETR4",
        "coverage_status": "FULL",
        "stock_fundamentals": {
            "pe": 4.5,
            "dividend_yield": 12.0,
        },
        "fii_indicators": None,
    }

    with patch(
        "app.services.asset_portfolio_insight_service.get_canonical_portfolio_positions",
        new=AsyncMock(return_value=mock_groups),
    ), patch(
        "app.services.asset_portfolio_insight_service.get_targets_map",
        new=AsyncMock(return_value=mock_targets),
    ), patch(
        "app.services.asset_portfolio_insight_service.asset_enrichment_service.get_asset_enrichment",
        new=AsyncMock(return_value=mock_enrichment),
    ):
        result = await insight_service.get_insight(
            db=mock_db,
            portfolio_id=1,
            user_id=10,
            ticker="PETR4",
        )

    assert result.ticker == "PETR4"
    pos = result.position
    assert pos.is_held is True
    assert pos.quantity == 500
    assert pos.average_price == 30.0
    assert pos.invested_value == 15000.0
    assert pos.current_value == 20000.0
    assert pos.capital_gain_value == 5000.0
    assert pos.capital_gain_percent == 33.33
    assert pos.dividends_received == 2000.0
    assert pos.total_return_value == 7000.0  # 5000 + 2000
    assert pos.total_return_percent == 46.67
    assert pos.portfolio_weight_percent == 20.0  # 20k / 100k
    assert pos.class_weight_percent == 50.0  # 20k / 40k
    assert pos.class_name == "ACAO"
    assert pos.class_current_allocation_percent == 40.0  # 40k / 100k
    assert pos.class_target_percent == 30.0
    assert pos.yield_on_cost_percent == 13.33  # 2000 / 15000

    # Insights
    ai = result.ai_insights
    assert ai.concentration_level == "HIGH"  # 20% > 15%
    assert "teto prudencial" in ai.concentration_message
    assert "sobre-alocada" in ai.rebalancing_guidance  # 40% vs meta 30%
    assert "dividendos/jcp" in ai.strategic_role.lower()
    assert "PETR4" in ai.explainable_summary


@pytest.mark.asyncio
async def test_get_insight_for_unheld_asset(insight_service) -> None:
    mock_db = AsyncMock()
    mock_groups: list[dict] = []
    mock_targets: dict[str, float] = {}
    mock_enrichment = {
        "ticker": "HGLG11",
        "coverage_status": "FULL",
        "fii_indicators": {"pvp": 1.05, "dividend_yield": 8.5},
        "stock_fundamentals": None,
    }

    with patch(
        "app.services.asset_portfolio_insight_service.get_canonical_portfolio_positions",
        new=AsyncMock(return_value=mock_groups),
    ), patch(
        "app.services.asset_portfolio_insight_service.get_targets_map",
        new=AsyncMock(return_value=mock_targets),
    ), patch(
        "app.services.asset_portfolio_insight_service.asset_enrichment_service.get_asset_enrichment",
        new=AsyncMock(return_value=mock_enrichment),
    ):
        result = await insight_service.get_insight(
            db=mock_db,
            portfolio_id=1,
            user_id=10,
            ticker="HGLG11",
        )

    assert result.ticker == "HGLG11"
    assert result.position.is_held is False
    assert result.ai_insights.concentration_level == "LOW"
    assert "não está presente" in result.ai_insights.concentration_message
    assert "8.50%" in result.ai_insights.income_assessment
