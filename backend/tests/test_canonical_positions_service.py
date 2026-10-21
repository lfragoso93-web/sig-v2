from unittest.mock import AsyncMock, patch

import pytest

from app.services.canonical_positions_service import (
    build_canonical_group_metrics,
    export_canonical_positions_csv,
    get_canonical_portfolio_positions,
)


def test_group_metrics_separate_capital_result_from_received_dividends():
    metrics = build_canonical_group_metrics(
        total_value=9_000,
        total_invested=10_000,
        received_dividends=350,
    )

    assert metrics == {
        "capital_result_value": -1_000,
        "capital_result_pct": -10.0,
        "received_dividends": 350,
        "total_result_value": -650,
        "total_result_pct": -6.5,
    }


def test_group_metrics_support_zero_invested_without_fake_percentage():
    metrics = build_canonical_group_metrics(
        total_value=0,
        total_invested=0,
        received_dividends=100,
    )

    assert metrics["capital_result_pct"] is None
    assert metrics["total_result_pct"] is None


@pytest.mark.asyncio
async def test_positions_remove_legacy_return_and_use_received_dividends():
    legacy = [
        {
            "label": "Ações",
            "total_value": 9_000,
            "total_invested": 10_000,
            "daily_variation_pct": 1.25,
            "rentabilidade_pct": 99.9,
            "positions": [{"ticker": "PETR4"}, {"ticker": "VALE3"}],
        }
    ]

    with (
        patch(
            "app.services.canonical_positions_service.get_portfolio_positions",
            new=AsyncMock(return_value=legacy),
        ),
        patch(
            "app.services.canonical_positions_service.load_received_entitlements_by_ticker",
            new=AsyncMock(return_value={"PETR4": 200, "VALE3": 150}),
        ),
    ):
        groups = await get_canonical_portfolio_positions(AsyncMock(), 7, 3)

    group = groups[0]
    assert "rentabilidade_pct" not in group
    assert group["daily_variation_pct"] == 1.25
    assert group["capital_result_pct"] == -10.0
    assert group["received_dividends"] == 350
    assert group["total_result_pct"] == -6.5
    assert group["performance_source"] == "intraday_valuation_and_received_dividends"


def test_export_canonical_positions_csv_empty():
    content = export_canonical_positions_csv([])
    lines = content.strip().splitlines()
    assert len(lines) == 1
    assert lines[0] == "classe,ticker,nome,quantidade,preco_medio,preco_atual,valor_investido,valor_atual,lucro_prejuizo_valor,lucro_prejuizo_pct,alocacao_pct,proventos_recebidos"


def test_export_canonical_positions_csv_multiclass():
    groups = [
        {
            "label": "Ações",
            "positions": [
                {
                    "ticker": "PETR4",
                    "asset_label": "Petrobras PN",
                    "quantity": 100,
                    "average_price_brl": 30.50,
                    "current_price_brl": 35.00,
                    "invested_value": 3050.0,
                    "current_value": 3500.0,
                    "variation_value": 450.0,
                    "variation_percent": 14.75,
                    "allocation_pct": 50.0,
                    "proventos": 120.0,
                }
            ],
        },
        {
            "label": "Renda Fixa",
            "positions": [
                {
                    "ticker": "CDB Banco Inter",
                    "asset_label": "CDB Inter 100% CDI",
                    "quantity": 1,
                    "average_price_brl": 1000.0,
                    "current_price_brl": 1050.0,
                    "invested_value": 1000.0,
                    "current_value": 1050.0,
                    "variation_value": 50.0,
                    "variation_percent": 5.0,
                    "allocation_pct": 15.0,
                    "proventos": 0.0,
                }
            ],
        },
    ]

    csv_content = export_canonical_positions_csv(groups)
    assert "Ações,PETR4,Petrobras PN,100,30.5,35.0,3050.0,3500.0,450.0,14.75,50.0,120.0" in csv_content
    assert "Renda Fixa,CDB Banco Inter,CDB Inter 100% CDI,1,1000.0,1050.0,1000.0,1050.0,50.0,5.0,15.0,0.0" in csv_content
