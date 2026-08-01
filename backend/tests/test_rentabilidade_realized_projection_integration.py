from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.models.transaction import OperationType
from app.services.rentabilidade_service import (
    _kpis_from_realtime,
    get_rentabilidade_por_ativo,
)


@pytest.mark.asyncio
async def test_realtime_kpis_use_canonical_realized_reader():
    db = AsyncMock()

    with (
        patch(
            "app.services.rentabilidade_service._positions_enriched_without_rf",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.rentabilidade_service.get_fixed_income_totals",
            new=AsyncMock(
                return_value={"invested_amount": 0.0, "current_value": 0.0}
            ),
        ),
        patch(
            "app.services.rentabilidade_service.load_realized_pnl_by_ticker",
            new=AsyncMock(return_value={"TEST3": 149.0}),
        ) as realized_reader,
        patch(
            "app.services.rentabilidade_service._proventos_totals",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
        patch(
            "app.services.rentabilidade_service._calc_invested_up_to",
            new=AsyncMock(return_value=0.0),
        ),
    ):
        payload = await _kpis_from_realtime(db, 7)

    assert payload["ganho_realizado"] == 149.0
    assert payload["total_pnl"] == 149.0
    realized_reader.assert_awaited_once_with(db, 7)


@pytest.mark.asyncio
async def test_asset_profitability_preserves_closed_position_from_canonical_reader():
    db = AsyncMock()
    buy = SimpleNamespace(
        operation=OperationType.buy,
        quantity=10,
        price=10,
        asset_type="ACAO",
    )

    with (
        patch(
            "app.services.rentabilidade_service.cache_get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.rentabilidade_service.cache_set",
            new=AsyncMock(),
        ),
        patch(
            "app.services.rentabilidade_service._load_transactions_by_ticker",
            new=AsyncMock(return_value=({"TEST3": [buy]}, [buy])),
        ),
        patch(
            "app.services.rentabilidade_service.load_realized_pnl_by_ticker",
            new=AsyncMock(return_value={"TEST3": 20.0}),
        ) as realized_reader,
        patch(
            "app.services.rentabilidade_service._positions_enriched_without_rf",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.rentabilidade_service.get_fixed_income_valuations",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await get_rentabilidade_por_ativo(db, 7)

    assert result == [
        {
            "ticker": "TEST3",
            "asset_type": "ACAO",
            "quantity": 0.0,
            "avg_price": 0.0,
            "current_price": 0.0,
            "total_invested": 100.0,
            "current_value": 0.0,
            "unrealized_pnl": 0.0,
            "unrealized_pct": 0.0,
            "realized_pnl": 20.0,
            "total_pnl": 20.0,
            "total_pct": 20.0,
            "total_pnl_pct": 20.0,
            "is_open": False,
        }
    ]
    realized_reader.assert_awaited_once_with(db, 7)
