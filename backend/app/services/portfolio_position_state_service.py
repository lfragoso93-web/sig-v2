"""Leitura canônica do estado de posições em uma data.

Mantém a projeção transaction-derived e eventos corporativos fora dos serviços de
valuation/snapshot para evitar dependências circulares e motores paralelos.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.snapshot_position_projection import project_snapshot_positions


class TickerState:
    """Estado projetado de um ticker em uma data."""

    __slots__ = ("ticker", "asset_type", "qty", "cost", "realized_pnl", "is_usd")

    def __init__(self, ticker: str, asset_type: str, is_usd: bool = False):
        self.ticker = ticker
        self.asset_type = asset_type
        self.qty = Decimal("0")
        self.cost = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.is_usd = is_usd


async def build_positions_at(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, TickerState]:
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return {}

    actions_by_ticker = await load_global_corporate_actions_by_ticker(
        db,
        [str(tx.ticker) for tx in transactions],
    )
    projections = project_snapshot_positions(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=target_date,
    )

    states: dict[str, TickerState] = {}
    for ticker, (projection, asset_type, is_usd) in projections.items():
        state = TickerState(ticker, asset_type, is_usd=is_usd)
        state.qty = projection.quantity
        state.cost = projection.total_cost
        state.realized_pnl = projection.realized_pnl
        states[ticker] = state

    return states
