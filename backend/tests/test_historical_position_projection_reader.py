from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.transaction import OperationType
from app.services.historical_position_projection_reader import (
    load_open_positions_as_of,
    load_position_timelines_as_of,
    load_realized_pnl_as_of,
)
from sqlalchemy.ext.asyncio import AsyncSession


def _tx(
    *,
    ticker: str,
    operation: OperationType,
    tx_date: date,
    quantity: str,
    price: str,
    fees: str = "0",
):
    return SimpleNamespace(
        id=1,
        ticker=ticker,
        operation=operation,
        date=tx_date,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal(fees),
        asset_type="ACAO",
        currency="BRL",
        fx_rate=None,
    )


@pytest.mark.asyncio
async def test_load_position_timelines_as_of_uses_cutoff_and_actions() -> None:
    db = AsyncMock(spec=AsyncSession)
    rows = [
        _tx(
            ticker="PETR4",
            operation=OperationType.buy,
            tx_date=date(2024, 1, 10),
            quantity="100",
            price="30",
        )
    ]
    result = MagicMock()
    result.scalars().all.return_value = rows
    db.execute.return_value = result

    with patch(
        "app.services.historical_position_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=AsyncMock(return_value={}),
    ) as load_actions:
        projected = await load_position_timelines_as_of(
            db,
            portfolio_id=7,
            target_date=date(2024, 12, 31),
        )

    assert projected["PETR4"][0].quantity == Decimal(100)
    load_actions.assert_awaited_once_with(db, ["PETR4"])


@pytest.mark.asyncio
async def test_load_open_positions_as_of_excludes_closed_tickers() -> None:
    db = AsyncMock(spec=AsyncSession)
    rows = [
        _tx(
            ticker="VALE3",
            operation=OperationType.buy,
            tx_date=date(2024, 1, 10),
            quantity="10",
            price="50",
        ),
        _tx(
            ticker="VALE3",
            operation=OperationType.sell,
            tx_date=date(2024, 6, 10),
            quantity="10",
            price="60",
        ),
    ]
    result = MagicMock()
    result.scalars().all.return_value = rows
    db.execute.return_value = result

    with patch(
        "app.services.historical_position_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=AsyncMock(return_value={}),
    ):
        projected = await load_open_positions_as_of(
            db,
            portfolio_id=7,
            target_date=date(2024, 12, 31),
        )

    assert projected == {}


@pytest.mark.asyncio
async def test_load_realized_pnl_as_of_keeps_closed_tickers() -> None:
    db = AsyncMock(spec=AsyncSession)
    rows = [
        _tx(
            ticker="VALE3",
            operation=OperationType.buy,
            tx_date=date(2024, 1, 10),
            quantity="10",
            price="50",
        ),
        _tx(
            ticker="VALE3",
            operation=OperationType.sell,
            tx_date=date(2024, 6, 10),
            quantity="10",
            price="60",
            fees="5",
        ),
    ]
    result = MagicMock()
    result.scalars().all.return_value = rows
    db.execute.return_value = result

    with patch(
        "app.services.historical_position_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=AsyncMock(return_value={}),
    ):
        projected = await load_realized_pnl_as_of(
            db,
            portfolio_id=7,
            target_date=date(2024, 12, 31),
        )

    assert projected == {"VALE3": 95.0}
