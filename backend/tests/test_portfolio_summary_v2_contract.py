from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.schemas.portfolio_summary import PortfolioSummaryResponse
from app.services import portfolio_summary_service
from app.services.portfolio_summary_service import (
    PortfolioSummaryInput,
    _build_summary_from_latest_snapshot,
    _validate_summary_contract,
    build_portfolio_summary,
)


LEGACY_FIELDS = {
    "total_invested",
    "current_value",
    "total_gain",
    "total_gain_pct",
    "proventos_em_carteira",
    "ganho_capital",
}


def test_financial_builder_does_not_emit_legacy_aliases() -> None:
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=10_000,
            current_value=11_000,
            realized_pnl=100,
            total_dividends=200,
        )
    )

    assert LEGACY_FIELDS.isdisjoint(summary)
    assert summary["ganho_nao_realizado"] == 1_000
    assert summary["ganho_realizado"] == 100
    assert summary["lucro_total"] == 1_300


def test_versioned_schema_rejects_unknown_legacy_field() -> None:
    payload = {
        "summary_version": "summary.v2",
        "total_patrimonio": 1_000,
        "total_investido": 900,
        "lucro_total": 120,
        "variacao_valor": 100,
        "variacao_percentual": 11.1111,
        "ganho_nao_realizado": 100,
        "ganho_realizado": 10,
        "rentabilidade_total": 2.5,
        "rentabilidade_acumulada": 2.5,
        "rentabilidade_diaria": 0.1,
        "rentabilidade_source": "snapshot_twr",
        "dividendos_recebidos_12m": 10,
        "total_proventos": 10,
        "proventos_as_of": "2026-07-16",
        "proventos_source": "received_cash_dividends",
        "has_partial_prices": False,
        "assets_without_price": [],
        "price_assets_total": 2,
        "price_assets_covered": 2,
        "price_coverage_pct": 100,
        "usd_brl_rate": 5.5,
        "valuation_mode": "intraday",
        "valuation_updated_at": "2026-07-16T14:30:00+00:00",
        "performance_as_of": "2026-07-15",
        "snapshot_id": 123,
        "snapshot_date": "2026-07-15",
        "summary_source": "intraday_valuation_with_snapshot_twr",
        "return_is_estimated": False,
        "is_reconciled": True,
        "reconciliation": {},
        "current_value": 1_000,
    }

    with pytest.raises(ValidationError):
        PortfolioSummaryResponse.model_validate(payload)


@pytest.mark.asyncio
async def test_snapshot_summary_validates_full_v2_contract(monkeypatch) -> None:
    snapshot = SimpleNamespace(
        id=123,
        snapshot_date=date(2026, 7, 15),
        market_value=Decimal("1000.00"),
        cost_basis=Decimal("900.00"),
        realized_pnl=Decimal("10.00"),
        dividends_accumulated=Decimal("10.00"),
        daily_return_pct=Decimal("0.100000"),
        accumulated_return_pct=Decimal("2.500000"),
        return_is_estimated=False,
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "_get_intraday_valuation",
        AsyncMock(return_value={
            "total_invested": 900.0,
            "current_value": 1000.0,
            "assets_without_price": ("SEMPR3",),
            "price_assets_total": 4,
            "price_assets_covered": 3,
            "price_coverage_pct": 75.0,
            "valuation_updated_at": "2026-07-16T14:30:00+00:00",
        }),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "_get_received_dividend_totals",
        AsyncMock(return_value=(10.0, 10.0)),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_usd_brl_today",
        AsyncMock(return_value=5.5),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_realized_pnl",
        AsyncMock(return_value=10.0),
    )

    summary = await _build_summary_from_latest_snapshot(AsyncMock(), 7, snapshot)
    validated = _validate_summary_contract(summary)

    assert validated["summary_version"] == "summary.v2"
    assert validated["snapshot_id"] == 123
    assert validated["price_assets_total"] == 4
    assert validated["price_assets_covered"] == 3
    assert validated["price_coverage_pct"] == 75.0
    assert validated["total_patrimonio"] == 1_000
    assert validated["total_investido"] == 900
    assert validated["lucro_total"] == 120
    assert validated["ganho_realizado"] == 10
    assert validated["rentabilidade_total"] == 2.5
    assert validated["total_proventos"] == 10
    assert validated["is_reconciled"] is True
    assert LEGACY_FIELDS.isdisjoint(validated)
