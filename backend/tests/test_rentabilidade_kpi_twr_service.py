from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.services.rentabilidade_kpi_service import (
    _period_twr,
    get_rentabilidade_kpis,
)


def test_period_twr_compounds_daily_returns():
    points = [
        {"date": "2026-07-01", "daily_return_pct": 2.0},
        {"date": "2026-07-02", "daily_return_pct": -1.0},
    ]

    assert _period_twr(points) == pytest.approx(0.98)


def test_period_twr_filters_before_start_date():
    points = [
        {"date": "2026-06-30", "daily_return_pct": 10.0},
        {"date": "2026-07-01", "daily_return_pct": 2.0},
        {"date": "2026-07-02", "daily_return_pct": -1.0},
    ]

    assert _period_twr(points, date(2026, 7, 1)) == pytest.approx(0.98)


@pytest.mark.asyncio
async def test_kpis_use_canonical_result_and_snapshot_twr():
    summary = {
        "total_patrimonio": 11000.0,
        "total_investido": 10000.0,
        "ganho_nao_realizado": 400.0,
        "lucro_total": 1300.0,
        "total_proventos": 500.0,
        "dividendos_recebidos_12m": 300.0,
    }
    points = [
        {
            "date": "2026-07-01",
            "daily_return_pct": 2.0,
            "accumulated_return_pct": 2.0,
            "return_is_estimated": True,
            "has_partial_prices": False,
        },
        {
            "date": date.today().isoformat(),
            "daily_return_pct": -1.0,
            "accumulated_return_pct": 0.98,
            "return_is_estimated": True,
            "has_partial_prices": True,
        },
    ]

    with (
        patch(
            "app.services.rentabilidade_kpi_service.get_canonical_portfolio_summary",
            new=AsyncMock(return_value=summary),
        ),
        patch(
            "app.services.rentabilidade_kpi_service.get_realized_pnl",
            new=AsyncMock(return_value=400.0),
        ),
        patch(
            "app.services.rentabilidade_kpi_service.get_enriched_daily_evolution",
            new=AsyncMock(return_value=points),
        ),
    ):
        payload = await get_rentabilidade_kpis(AsyncMock(), 7, 3)

    assert payload["total_pnl"] == 1300.0
    assert payload["ganho_realizado"] == 400.0
    assert payload["proventos_total"] == 500.0
    assert payload["retorno_dia_pct"] == -1.0
    assert payload["retorno_desde_inicio_pct"] == pytest.approx(0.98)
    assert payload["retorno_total_pct"] == pytest.approx(0.98)
    assert payload["return_is_estimated"] is True
    assert payload["has_partial_prices"] is True
