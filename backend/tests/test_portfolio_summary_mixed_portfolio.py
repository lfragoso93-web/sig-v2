from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import portfolio_summary_service
from app.services.portfolio_summary_service import _build_summary_from_latest_snapshot


@pytest.mark.asyncio
async def test_mixed_portfolio_uses_intraday_valuation_and_closed_twr(monkeypatch) -> None:
    enriched_positions = [
        {
            "ticker": "PETR4",
            "asset_type": "ACAO",
            "total_invested": 1_000.0,
            "current_value": 1_100.0,
            "current_price": 11.0,
        },
        {
            "ticker": "TESOURO-SELIC-2029",
            "asset_type": "TESOURO_DIRETO",
            "total_invested": 2_000.0,
            "current_value": 2_100.0,
            "current_price": 14_000.0,
        },
        {
            "ticker": "AAPL",
            "asset_type": "STOCK",
            "total_invested": 5_000.0,
            "current_value": 5_500.0,
            "current_price": 200.0,
        },
    ]
    fixed_income_totals = {
        "invested_amount": Decimal("3000.00"),
        "current_value": Decimal("3150.00"),
    }

    monkeypatch.setattr(
        portfolio_summary_service,
        "_non_fixed_income_enriched",
        AsyncMock(return_value=enriched_positions),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_fixed_income_totals",
        AsyncMock(return_value=fixed_income_totals),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "_get_received_dividend_totals",
        AsyncMock(return_value=(100.0, 250.0)),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_realized_pnl",
        AsyncMock(return_value=300.0),
    )
    monkeypatch.setattr(
        portfolio_summary_service,
        "get_usd_brl_today",
        AsyncMock(return_value=5.4),
    )

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: datetime(2026, 7, 18, 15, 30, tzinfo=timezone.utc),
    )
    snapshot = SimpleNamespace(
        id=99,
        snapshot_date=date(2026, 7, 17),
        market_value=Decimal("11700.00"),
        cost_basis=Decimal("10800.00"),
        realized_pnl=Decimal("250.00"),
        dividends_accumulated=Decimal("200.00"),
        daily_return_pct=Decimal("0.150000"),
        accumulated_return_pct=Decimal("8.250000"),
        return_is_estimated=False,
    )

    summary = await _build_summary_from_latest_snapshot(db, 7, snapshot)

    assert summary["total_investido"] == 11_000
    assert summary["total_patrimonio"] == 11_850
    assert summary["ganho_nao_realizado"] == 850
    assert summary["ganho_realizado"] == 300
    assert summary["total_proventos"] == 250
    assert summary["lucro_total"] == 1_400
    assert summary["rentabilidade_total"] == 8.25
    assert summary["rentabilidade_source"] == "snapshot_twr"
    assert summary["price_assets_total"] == 3
    assert summary["price_assets_covered"] == 3
    assert summary["price_coverage_pct"] == 100
    assert summary["assets_without_price"] == []
    assert summary["valuation_mode"] == "intraday"
    assert summary["performance_as_of"] == "2026-07-17"
