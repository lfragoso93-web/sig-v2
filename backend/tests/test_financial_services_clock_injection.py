"""Testes de determinismo e injeção canônica de Clock (SGI013 / OP-06)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.clock import FrozenClock
from app.services.portfolio_analysis_service import _compute_class_fixed_income
from app.services.rentabilidade_kpi_service import get_rentabilidade_kpis


@pytest.mark.asyncio
async def test_rentabilidade_kpis_respects_injected_clock() -> None:
    frozen_dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    clock = FrozenClock(current=frozen_dt)

    summary_mock = {
        "total_patrimonio": 100000.0,
        "total_investido": 80000.0,
        "ganho_nao_realizado": 20000.0,
        "ganho_realizado": 5000.0,
        "lucro_total": 25000.0,
        "total_proventos": 4000.0,
        "dividendos_recebidos_12m": 3500.0,
        "valuation_updated_at": "2025-06-15T12:00:00",
        "proventos_as_of": "2025-06-15",
    }

    mock_db = AsyncMock()

    with (
        patch(
            "app.services.rentabilidade_kpi_service.get_canonical_portfolio_summary",
            new=AsyncMock(return_value=summary_mock),
        ),
        patch(
            "app.services.rentabilidade_kpi_service.get_enriched_daily_evolution",
            new=AsyncMock(return_value=[
                {"date": "2025-06-01", "daily_return_pct": "0.01", "accumulated_return_pct": "0.05"},
                {"date": "2025-06-15", "daily_return_pct": "0.005", "accumulated_return_pct": "0.055"},
            ]),
        ),
    ):
        result = await get_rentabilidade_kpis(
            mock_db,
            portfolio_id=10,
            user_id=1,
            clock=clock,
        )

        assert result["contract_version"] == "rentabilidade.v2"
        assert result["patrimonio_atual"] == 100000.0
        assert result["performance_as_of"] == "2025-06-15"


def test_portfolio_analysis_fixed_income_respects_injected_clock() -> None:
    frozen_dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    clock = FrozenClock(current=frozen_dt)

    class DummyPosition:
        current_value = 10000.0
        invested_value = 10000.0
        indexer = "CDI"
        ticker = "CDB_TEST"
        maturity_date = None

    analysis = _compute_class_fixed_income(
        positions=[DummyPosition()],
        asset_type="RENDA_FIXA",
        class_total_value=10000.0,
        clock=clock,
    )

    assert analysis.is_applicable is True
    assert analysis.cdi_allocation_pct == 100.0
