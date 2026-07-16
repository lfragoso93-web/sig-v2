"""Contrato financeiro do Resumo híbrido: valuation intradiário e TWR fechado."""
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


def test_build_summary_preserves_financial_contract() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=11_500,
            realized_pnl=400,
            total_dividends=600,
        )
    )
    assert summary["total_patrimonio"] == 11_500
    assert summary["total_investido"] == 10_000
    assert summary["variacao_valor"] == 1_500
    assert summary["lucro_total"] == 2_500
    assert summary["rentabilidade_total"] == 25
    assert summary["rentabilidade_source"] == "valuation_fallback"


def test_snapshot_twr_overrides_simple_return() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=15_000,
            realized_pnl=2_000,
            total_dividends=1_000,
            accumulated_twr_pct=12.345678,
            daily_twr_pct=-0.1234567,
        )
    )
    assert summary["lucro_total"] == 8_000
    assert summary["rentabilidade_total"] == 12.3457
    assert summary["rentabilidade_diaria"] == -0.123457
    assert summary["rentabilidade_source"] == "snapshot_twr"


def test_negative_values_keep_signs() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=8_500,
            realized_pnl=-200,
            total_dividends=100,
        )
    )
    assert summary["variacao_valor"] == -1_500
    assert summary["lucro_total"] == -1_600
    assert summary["rentabilidade_total"] == -16


def test_zero_cost_snapshot_preserves_twr() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=0,
            current_value=0,
            accumulated_twr_pct=8.765432,
            daily_twr_pct=0.25,
        )
    )
    assert summary["rentabilidade_total"] == 8.7654
    assert summary["rentabilidade_diaria"] == 0.25


@pytest.mark.asyncio
async def test_intraday_valuation_is_used_with_closed_snapshot_twr(monkeypatch) -> None:
    snapshot = SimpleNamespace(
        snapshot_date=date(2026, 7, 15),
        market_value=Decimal("12000.00"),
        cost_basis=Decimal("10000.00"),
        realized_pnl=Decimal("300.00"),
        dividends_accumulated=Decimal("700.00"),
        daily_return_pct=Decimal("0.345678"),
        accumulated_return_pct=Decimal("9.876543"),
        return_is_estimated=False,
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "_get_intraday_valuation",
        AsyncMock(return_value={
            "total_invested": 10_200.0,
            "current_value": 12_800.0,
            "assets_without_price": (),
            "valuation_updated_at": "2026-07-16T14:30:00+00:00",
        }),
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

    summary = await _build_summary_from_latest_snapshot(AsyncMock(), 7, snapshot)

    assert summary["total_patrimonio"] == 12_800
    assert summary["total_investido"] == 10_200
    assert summary["variacao_valor"] == 2_600
    assert summary["rentabilidade_total"] == 9.8765
    assert summary["performance_as_of"] == "2026-07-15"
    assert summary["valuation_mode"] == "intraday"
    assert summary["valuation_updated_at"] == "2026-07-16T14:30:00+00:00"
    assert summary["summary_source"] == "intraday_valuation_with_snapshot_twr"
    assert summary["reconciliation"]["valuation_reconciliation_status"] == "not_comparable_intraday"
    assert summary["reconciliation"]["failed_fields"] == []


@pytest.mark.asyncio
async def test_intraday_summary_does_not_compare_market_value_to_closed_snapshot(monkeypatch) -> None:
    snapshot = SimpleNamespace(
        snapshot_date=date(2026, 7, 15),
        market_value=Decimal("1000.00"),
        cost_basis=Decimal("900.00"),
        realized_pnl=Decimal("0.00"),
        dividends_accumulated=Decimal("0.00"),
        daily_return_pct=Decimal("0.100000"),
        accumulated_return_pct=Decimal("1.000000"),
        return_is_estimated=True,
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "_get_intraday_valuation",
        AsyncMock(return_value={
            "total_invested": 900.0,
            "current_value": 1250.0,
            "assets_without_price": (),
            "valuation_updated_at": None,
        }),
    )
    monkeypatch.setattr(portfolio_summary_service, "sum_dividends", AsyncMock(return_value=0.0))
    monkeypatch.setattr(portfolio_summary_service, "get_usd_brl_today", AsyncMock(return_value=1.0))

    summary = await _build_summary_from_latest_snapshot(AsyncMock(), 1, snapshot)

    assert summary["total_patrimonio"] == 1250.0
    assert summary["is_reconciled"] is True
    assert summary["reconciliation"]["valuation_comparable_to_snapshot"] is False
