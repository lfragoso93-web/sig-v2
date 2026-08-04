from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.transaction import OperationType
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.realized_pnl_projection_reader import (
    load_realized_disposals,
    load_realized_pnl_by_ticker,
)


def _tx(
    *,
    ticker: str = "TEST3",
    operation: OperationType,
    day: int,
    quantity: str,
    price: str,
    fees: str = "0",
    asset_type: str = "ACAO",
):
    return SimpleNamespace(
        id=day,
        portfolio_id=7,
        ticker=ticker,
        asset_type=asset_type,
        operation=operation,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal(fees),
        date=date(2026, 1, day),
        currency="BRL",
        fx_rate=None,
    )


def _split() -> NormalizedCorporateAction:
    return NormalizedCorporateAction(
        source="test",
        source_event_id="split-2",
        ticker="TEST3",
        event_date=date(2026, 1, 2),
        kind=CorporateActionKind.SPLIT,
        quantity_factor=Decimal(2),
        raw_payload={},
    )


@pytest.mark.asyncio
async def test_realized_reader_applies_split_and_sale_fees():
    db = AsyncMock()
    result = MagicMock()
    result.scalars().all.return_value = [
        _tx(
            operation=OperationType.buy,
            day=1,
            quantity="100",
            price="10",
        ),
        _tx(
            operation=OperationType.sell,
            day=3,
            quantity="50",
            price="8",
            fees="1",
        ),
    ]
    db.execute.return_value = result

    with patch(
        "app.services.realized_pnl_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=AsyncMock(return_value={"TEST3": (_split(),)}),
    ) as loader:
        realized = await load_realized_pnl_by_ticker(db, 7)

    assert realized == {"TEST3": 149.0}
    loader.assert_awaited_once_with(db, ["TEST3", "TEST3"])


@pytest.mark.asyncio
async def test_realized_reader_preserves_closed_position_result():
    db = AsyncMock()
    result = MagicMock()
    result.scalars().all.return_value = [
        _tx(
            operation=OperationType.buy,
            day=1,
            quantity="10",
            price="10",
        ),
        _tx(
            operation=OperationType.sell,
            day=2,
            quantity="10",
            price="12",
        ),
    ]
    db.execute.return_value = result

    with patch(
        "app.services.realized_pnl_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=AsyncMock(return_value={}),
    ):
        realized = await load_realized_pnl_by_ticker(db, 7)

    assert realized == {"TEST3": 20.0}


@pytest.mark.asyncio
async def test_realized_reader_ignores_fixed_income_transactions():
    db = AsyncMock()
    result = MagicMock()
    result.scalars().all.return_value = [
        _tx(
            operation=OperationType.buy,
            day=1,
            quantity="1",
            price="1000",
            asset_type="RENDA_FIXA",
        )
    ]
    db.execute.return_value = result

    loader = AsyncMock()
    with patch(
        "app.services.realized_pnl_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=loader,
    ):
        realized = await load_realized_pnl_by_ticker(db, 7)

    assert realized == {}
    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_detailed_reader_preserves_history_and_filters_disposal_period():
    db = AsyncMock()
    result = MagicMock()
    result.scalars().all.return_value = [
        _tx(
            operation=OperationType.buy,
            day=1,
            quantity="10",
            price="10",
        ),
        _tx(
            operation=OperationType.sell,
            day=3,
            quantity="4",
            price="15",
            fees="1",
        ),
    ]
    db.execute.return_value = result

    with patch(
        "app.services.realized_pnl_projection_reader."
        "load_global_corporate_actions_by_ticker",
        new=AsyncMock(return_value={}),
    ):
        disposals = await load_realized_disposals(
            db,
            7,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 31),
        )

    assert len(disposals) == 1
    disposal = disposals[0]
    assert disposal.transaction_id == 3
    assert disposal.ticker == "TEST3"
    assert disposal.asset_type == "ACAO"
    assert disposal.disposal_date == date(2026, 1, 3)
    assert disposal.quantity_disposed == Decimal(4)
    assert disposal.realized_pnl_brl == Decimal(19)


@pytest.mark.asyncio
async def test_detailed_reader_rejects_inverted_period():
    with pytest.raises(ValueError, match="end_date"):
        await load_realized_disposals(
            AsyncMock(),
            7,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 31),
        )
