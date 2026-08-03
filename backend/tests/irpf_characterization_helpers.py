"""Fixtures leves compartilhadas pelos testes de caracterização fiscal."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType


def transaction(
    *,
    ticker: str,
    operation: OperationType,
    quantity: float,
    price: float,
    tx_date: date,
    asset_type: str = "ETF",
    fees: float = 0.0,
) -> MagicMock:
    item = MagicMock()
    item.ticker = ticker
    item.operation = operation
    item.asset_type = asset_type
    item.quantity = quantity
    item.price = price
    item.date = tx_date
    item.currency = "BRL"
    item.fees = fees
    return item


def db_with_transactions(
    *,
    current_year: list[MagicMock],
    previous_years: list[MagicMock] | None = None,
) -> AsyncMock:
    current_result = MagicMock()
    current_result.scalars().all.return_value = current_year
    previous_result = MagicMock()
    previous_result.scalars().all.return_value = previous_years or []

    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [current_result, previous_result]
    return db
