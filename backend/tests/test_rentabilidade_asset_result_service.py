from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.rentabilidade_asset_result_service import get_canonical_asset_results


@pytest.mark.asyncio
async def test_asset_results_use_canonical_positions_and_realized_pnl():
    groups = [{
        "positions": [{
            "ticker": "TEST3",
            "asset_label": "Teste",
            "asset_type": "ACAO",
            "quantity": 10,
            "average_price": 10,
            "current_price": 12,
            "invested_value": 100,
            "current_value": 120,
        }]
    }]
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    with patch(
        "app.services.rentabilidade_asset_result_service.get_canonical_portfolio_positions",
        AsyncMock(return_value=groups),
    ), patch(
        "app.services.rentabilidade_asset_result_service.get_realized_pnl_by_ticker",
        AsyncMock(return_value={"TEST3": 5.0}),
    ):
        rows = await get_canonical_asset_results(db, 1, 2)

    assert rows == [{
        "ticker": "TEST3",
        "name": "Teste",
        "asset_type": "ACAO",
        "quantity": 10.0,
        "avg_price": 10.0,
        "current_price": 12,
        "total_invested": 100.0,
        "current_value": 120.0,
        "unrealized_pnl": 20.0,
        "unrealized_pct": 20.0,
        "realized_pnl": 5.0,
        "total_pnl": 25.0,
        "total_pnl_pct": 25.0,
        "is_open": True,
        "result_source": "canonical_positions_and_realized_pnl",
    }]


@pytest.mark.asyncio
async def test_closed_position_keeps_realized_result_without_fake_twr():
    tx = SimpleNamespace(
        ticker="OLD3",
        asset_type="ACAO",
        operation="buy",
        quantity=10,
        price=8,
        fees=0,
        fx_rate=1,
    )
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = [tx]

    with patch(
        "app.services.rentabilidade_asset_result_service.get_canonical_portfolio_positions",
        AsyncMock(return_value=[]),
    ), patch(
        "app.services.rentabilidade_asset_result_service.get_realized_pnl_by_ticker",
        AsyncMock(return_value={"OLD3": 20.0}),
    ):
        rows = await get_canonical_asset_results(db, 1, 2)

    assert rows[0]["is_open"] is False
    assert rows[0]["realized_pnl"] == 20.0
    assert rows[0]["total_pnl_pct"] == 25.0
    assert "twr" not in rows[0]
