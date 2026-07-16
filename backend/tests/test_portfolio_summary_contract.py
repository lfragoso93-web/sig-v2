"""Contrato financeiro dos KPIs consolidados da carteira.

Estes testes documentam a semantica atual que deve ser preservada durante a
migracao do endpoint de Resumo para os snapshots canonicos.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import portfolio_summary_service
from app.services.portfolio_summary_service import (
    PortfolioSummaryInput,
    _build_summary_from_latest_snapshot,
    build_portfolio_summary,
)


CANONICAL_KEYS = {
    "total_patrimonio",
    "total_investido",
    "lucro_total",
    "variacao_valor",
    "variacao_percentual",
    "rentabilidade_total",
    "dividendos_recebidos_12m",
    "total_proventos",
    "proventos_em_carteira",
    "ganho_capital",
    "ganho_nao_realizado",
    "ganho_realizado",
    "has_partial_prices",
    "assets_without_price",
    "usd_brl_rate",
}

LEGACY_ALIAS_KEYS = {
    "total_invested",
    "current_value",
    "total_gain",
    "total_gain_pct",
}


def test_contract_exposes_canonical_fields_and_temporary_legacy_aliases() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(total_invested=1_000, current_value=1_100)
    )

    assert CANONICAL_KEYS <= summary.keys()
    assert LEGACY_ALIAS_KEYS <= summary.keys()


def test_patrimonio_and_invested_capital_are_preserved() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(total_invested=12_345.678, current_value=13_456.789)
    )

    assert summary["total_patrimonio"] == 13_456.79
    assert summary["total_investido"] == 12_345.68


def test_variation_represents_only_unrealized_result() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=11_500,
            realized_pnl=400,
            total_dividends=600,
        )
    )

    assert summary["variacao_valor"] == 1_500
    assert summary["variacao_percentual"] == 15
    assert summary["ganho_nao_realizado"] == 1_500
    assert summary["ganho_capital"] == 1_500


def test_total_result_combines_unrealized_realized_and_dividends() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=11_500,
            realized_pnl=400,
            total_dividends=600,
        )
    )

    assert summary["ganho_realizado"] == 400
    assert summary["total_proventos"] == 600
    assert summary["lucro_total"] == 2_500


def test_current_total_return_is_profit_over_employed_capital() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=11_500,
            realized_pnl=400,
            total_dividends=600,
        )
    )

    # Contrato temporario: ainda nao representa o TWR dos snapshots.
    assert summary["rentabilidade_total"] == 25


def test_negative_portfolio_keeps_negative_signs() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=8_500,
            realized_pnl=-200,
            total_dividends=100,
        )
    )

    assert summary["variacao_valor"] == -1_500
    assert summary["variacao_percentual"] == -15
    assert summary["lucro_total"] == -1_600
    assert summary["rentabilidade_total"] == -16


def test_zero_invested_capital_does_not_divide_by_zero() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=0,
            current_value=0,
            realized_pnl=250,
            total_dividends=50,
        )
    )

    assert summary["variacao_percentual"] == 0
    assert summary["rentabilidade_total"] == 0
    assert summary["lucro_total"] == 300


def test_dividend_periods_remain_independent() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=1_000,
            current_value=1_000,
            dividends_12m=120.456,
            total_dividends=450.789,
        )
    )

    assert summary["dividendos_recebidos_12m"] == 120.46
    assert summary["total_proventos"] == 450.79


def test_price_coverage_metadata_is_preserved() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=1_000,
            current_value=1_000,
            has_partial_prices=True,
            assets_without_price=("ABCD3", "XPTO11"),
            usd_brl_rate=5.43219,
        )
    )

    assert summary["has_partial_prices"] is True
    assert summary["assets_without_price"] == ["ABCD3", "XPTO11"]
    assert summary["usd_brl_rate"] == 5.4322


@pytest.mark.parametrize(
    ("canonical", "legacy"),
    [
        ("total_investido", "total_invested"),
        ("total_patrimonio", "current_value"),
        ("variacao_valor", "total_gain"),
        ("variacao_percentual", "total_gain_pct"),
    ],
)
def test_legacy_aliases_match_their_canonical_fields(
    canonical: str,
    legacy: str,
) -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(total_invested=2_000, current_value=2_250)
    )

    assert summary[legacy] == summary[canonical]


@pytest.mark.asyncio
async def test_latest_snapshot_is_primary_source_for_summary(monkeypatch) -> None:
    snapshot = SimpleNamespace(
        snapshot_date=date(2026, 7, 16),
        market_value=Decimal("12500.00"),
        cost_basis=Decimal("10000.00"),
        realized_pnl=Decimal("300.00"),
        dividends_accumulated=Decimal("700.00"),
        has_partial_prices=True,
        return_is_estimated=False,
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "sum_dividends",
        AsyncMock(return_value=Decimal("180.00")),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_usd_brl_today",
        AsyncMock(return_value=5.55),
    )

    summary = await _build_summary_from_latest_snapshot(
        AsyncMock(),
        portfolio_id=7,
        snapshot=snapshot,
    )

    assert summary["total_patrimonio"] == 12_500
    assert summary["total_investido"] == 10_000
    assert summary["variacao_valor"] == 2_500
    assert summary["ganho_realizado"] == 300
    assert summary["total_proventos"] == 700
    assert summary["lucro_total"] == 3_500
    assert summary["dividendos_recebidos_12m"] == 180
    assert summary["has_partial_prices"] is True
    assert summary["snapshot_date"] == "2026-07-16"
    assert summary["summary_source"] == "portfolio_snapshot"
    assert summary["return_is_estimated"] is False


@pytest.mark.asyncio
async def test_snapshot_summary_does_not_recompute_positions(monkeypatch) -> None:
    snapshot = SimpleNamespace(
        snapshot_date=date(2026, 7, 16),
        market_value=Decimal("1000.00"),
        cost_basis=Decimal("900.00"),
        realized_pnl=Decimal("0.00"),
        dividends_accumulated=Decimal("0.00"),
        has_partial_prices=False,
        return_is_estimated=True,
    )
    positions = AsyncMock(side_effect=AssertionError("positions must not be queried"))
    fixed_income = AsyncMock(side_effect=AssertionError("valuation must not be queried"))
    monkeypatch.setattr(portfolio_summary_service, "_non_fixed_income_enriched", positions)
    monkeypatch.setattr(portfolio_summary_service, "get_fixed_income_totals", fixed_income)
    monkeypatch.setattr(
        portfolio_summary_service,
        "sum_dividends",
        AsyncMock(return_value=Decimal("0.00")),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_usd_brl_today",
        AsyncMock(return_value=1.0),
    )

    await _build_summary_from_latest_snapshot(AsyncMock(), 1, snapshot)

    positions.assert_not_awaited()
    fixed_income.assert_not_awaited()
