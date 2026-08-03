from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.transaction import OperationType
from app.services.rentabilidade_service import (
    _kpis_from_realtime,
    _load_net_contributed_up_to,
)


@pytest.mark.asyncio
async def test_runtime_cash_flow_uses_net_sale_proceeds():
    transactions = [
        SimpleNamespace(
            operation=OperationType.buy,
            quantity=10,
            price=100,
            fees=10,
            asset_type="ACAO",
            currency="BRL",
            fx_rate=None,
        ),
        SimpleNamespace(
            operation=OperationType.sell,
            quantity=4,
            price=150,
            fees=5,
            asset_type="ACAO",
            currency="BRL",
            fx_rate=None,
        ),
    ]
    scalar_result = MagicMock()
    scalar_result.all.return_value = transactions
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalar_result
    db = AsyncMock()
    db.execute.return_value = execute_result

    result = await _load_net_contributed_up_to(db, 7, date(2026, 7, 31))

    assert result == 415.0
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_realtime_period_fallbacks_use_net_contributed_reader():
    reader = AsyncMock(side_effect=[800.0, 500.0])

    with (
        patch(
            "app.services.rentabilidade_service._positions_enriched_without_rf",
            new=AsyncMock(
                return_value=[
                    {
                        "total_invested": 1000.0,
                        "current_value": 1200.0,
                    }
                ]
            ),
        ),
        patch(
            "app.services.rentabilidade_service.get_fixed_income_totals",
            new=AsyncMock(
                return_value={"invested_amount": 0.0, "current_value": 0.0}
            ),
        ),
        patch(
            "app.services.rentabilidade_service.load_realized_pnl_by_ticker",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.services.rentabilidade_service._proventos_totals",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
        patch(
            "app.services.rentabilidade_service.utc_today",
            return_value=date(2026, 8, 1),
        ),
        patch(
            "app.services.rentabilidade_service._load_net_contributed_up_to",
            new=reader,
        ),
    ):
        result = await _kpis_from_realtime(AsyncMock(), 7)

    assert result["retorno_mes_pct"] == 50.0
    assert result["retorno_12m_pct"] == 140.0
    assert reader.await_args_list[0].args[2] == date(2026, 7, 31)
    assert reader.await_args_list[1].args[2] == date(2025, 8, 1)
