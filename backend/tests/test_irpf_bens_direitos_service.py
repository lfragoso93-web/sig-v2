from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.transaction import OperationType
from app.services.irpf_bens_direitos_service import calc_bens_direitos
from app.services.position_timeline_projection import PositionTimelineProjection
from sqlalchemy.ext.asyncio import AsyncSession


def _projection(*, quantity: str, total_cost: str) -> PositionTimelineProjection:
    return PositionTimelineProjection(
        quantity=Decimal(quantity),
        total_cost=Decimal(total_cost),
        total_cost_original_currency=Decimal(0),
        realized_pnl=Decimal(0),
        applied_event_ids=(),
        subscription_event_ids=(),
    )


@pytest.mark.asyncio
async def test_calc_bens_direitos_uses_canonical_cutoff_projection() -> None:
    db = AsyncMock(spec=AsyncSession)
    empty = MagicMock()
    empty.scalars().all.return_value = []
    db.execute.return_value = empty

    with patch(
        "app.services.irpf_bens_direitos_service.load_open_positions_as_of",
        new=AsyncMock(
            return_value={
                "PETR4": (_projection(quantity="150", total_cost="4515"), "ACAO", False),
                "AAPL": (_projection(quantity="2", total_cost="1900"), "STOCK", True),
            }
        ),
    ) as load_positions:
        bens = await calc_bens_direitos(db, portfolio_id=7, year=2024)

    load_positions.assert_awaited_once_with(db, 7, date(2024, 12, 31))
    by_ticker = {item.ticker: item for item in bens}
    assert by_ticker["PETR4"].quantidade == 150
    assert by_ticker["PETR4"].custo_medio == 30.1
    assert by_ticker["PETR4"].custo_total == 4515
    assert by_ticker["PETR4"].moeda == "BRL"
    assert by_ticker["AAPL"].moeda == "USD"


@pytest.mark.asyncio
async def test_calc_bens_direitos_preserves_fixed_income_until_dedicated_reader() -> None:
    db = AsyncMock(spec=AsyncSession)
    rf_buy = SimpleNamespace(
        id=1,
        ticker="CDB-2028",
        operation=OperationType.buy,
        asset_type="RENDA_FIXA",
        date=date(2024, 2, 1),
        quantity=Decimal(1),
        price=Decimal(1000),
        fees=Decimal(0),
        currency="BRL",
    )
    rows = MagicMock()
    rows.scalars().all.return_value = [rf_buy]
    db.execute.return_value = rows

    with patch(
        "app.services.irpf_bens_direitos_service.load_open_positions_as_of",
        new=AsyncMock(return_value={}),
    ):
        bens = await calc_bens_direitos(db, portfolio_id=7, year=2024)

    assert len(bens) == 1
    assert bens[0].ticker == "CDB-2028"
    assert bens[0].asset_type == "RENDA_FIXA"
    assert bens[0].custo_total == 1000
