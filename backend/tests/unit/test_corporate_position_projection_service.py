from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType
from app.services.corporate_position_projection_service import (
    EligibleQuantityAction,
    consume_quantity_actions,
)
from app.services.portfolio_service import calc_raw_positions
from app.services.portfolio_snapshot_service import _build_positions_at


def _action(event_id: int, event_date: date, factor: str) -> EligibleQuantityAction:
    return EligibleQuantityAction(
        event_id=event_id,
        ticker="PETR4",
        effective_date=event_date,
        event_type="DESDOBRAMENTO",
        quantity_factor=Decimal(factor),
    )


def test_consumer_applies_only_events_through_reference_date_once() -> None:
    actions = (
        _action(1, date(2024, 3, 1), "2"),
        _action(2, date(2025, 1, 1), "0.5"),
    )

    quantity, cursor, applied = consume_quantity_actions(
        actions,
        cursor=0,
        through_date=date(2024, 12, 31),
        quantity=Decimal(100),
    )
    quantity, cursor, second_applied = consume_quantity_actions(
        actions,
        cursor=cursor,
        through_date=date(2025, 12, 31),
        quantity=quantity,
    )

    assert quantity == Decimal("100.0")
    assert cursor == 2
    assert applied == (1,)
    assert second_applied == (2,)


@pytest.mark.asyncio
async def test_current_position_interleaves_split_between_buy_and_sell() -> None:
    buy = MagicMock(
        ticker="PETR4",
        operation=OperationType.buy,
        asset_type="ACAO",
        quantity=100.0,
        price=10.0,
        fees=0.0,
        date=date(2024, 1, 10),
        currency="BRL",
        fx_rate=None,
    )
    sell = MagicMock(
        ticker="PETR4",
        operation=OperationType.sell,
        asset_type="ACAO",
        quantity=50.0,
        price=6.0,
        fees=0.0,
        date=date(2024, 6, 1),
        currency="BRL",
        fx_rate=None,
    )
    result = MagicMock()
    result.scalars().all.return_value = [buy, sell]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = result
    actions = {"PETR4": (_action(7, date(2024, 3, 1), "2"),)}

    with patch(
        "app.services.portfolio_service.load_eligible_quantity_actions",
        new=AsyncMock(return_value=actions),
    ):
        positions = await calc_raw_positions(db, portfolio_id=1)

    assert len(positions) == 1
    assert positions[0]["quantity"] == 150.0
    assert positions[0]["total_invested"] == 750.0
    assert positions[0]["avg_price"] == 5.0


@pytest.mark.asyncio
async def test_purchase_after_historical_split_is_not_transformed() -> None:
    buy = MagicMock(
        ticker="PETR4",
        operation=OperationType.buy,
        asset_type="ACAO",
        quantity=100.0,
        price=10.0,
        fees=0.0,
        date=date(2024, 6, 1),
        currency="BRL",
        fx_rate=None,
    )
    result = MagicMock()
    result.scalars().all.return_value = [buy]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = result
    actions = {"PETR4": (_action(7, date(2024, 3, 1), "2"),)}

    with patch(
        "app.services.portfolio_service.load_eligible_quantity_actions",
        new=AsyncMock(return_value=actions),
    ):
        positions = await calc_raw_positions(db, portfolio_id=1)

    assert positions[0]["quantity"] == 100.0
    assert positions[0]["avg_price"] == 10.0


@pytest.mark.asyncio
async def test_snapshot_position_uses_same_chronological_projection() -> None:
    buy = MagicMock(
        ticker="PETR4",
        operation=OperationType.buy,
        asset_type="ACAO",
        quantity=100.0,
        price=10.0,
        fees=0.0,
        date=date(2024, 1, 10),
        currency="BRL",
        fx_rate=None,
    )
    sell = MagicMock(
        ticker="PETR4",
        operation=OperationType.sell,
        asset_type="ACAO",
        quantity=50.0,
        price=6.0,
        fees=0.0,
        date=date(2024, 6, 1),
        currency="BRL",
        fx_rate=None,
    )
    result = MagicMock()
    result.scalars().all.return_value = [buy, sell]
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = result
    actions = {"PETR4": (_action(7, date(2024, 3, 1), "2"),)}

    with patch(
        "app.services.portfolio_snapshot_service.load_eligible_quantity_actions",
        new=AsyncMock(return_value=actions),
    ):
        states = await _build_positions_at(
            db, portfolio_id=1, target_date=date(2024, 12, 31)
        )

    assert states["PETR4"].qty == Decimal("150.0")
    assert states["PETR4"].cost == Decimal("750.00")
    assert states["PETR4"].avg_price == Decimal("5.0")
