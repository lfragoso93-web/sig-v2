"""Leitura read-only de posições e resultado projetados em uma data de corte."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.portfolio_service import normalize_type
from app.services.snapshot_position_projection import project_transaction_timelines

_RENDA_FIXA_TYPE = "RENDA_FIXA"


async def load_position_timelines_as_of(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
):
    """Projeta todas as linhas temporais até ``target_date``.

    Inclui tickers já encerrados para permitir leitura de resultado realizado.
    Renda Fixa permanece fora deste projetor porque usa motor dedicado.
    """

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = [
        tx
        for tx in result.scalars().all()
        if normalize_type(tx.asset_type) != _RENDA_FIXA_TYPE
    ]
    if not transactions:
        return {}

    actions_by_ticker = await load_global_corporate_actions_by_ticker(
        db,
        [str(tx.ticker) for tx in transactions],
    )
    return project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=target_date,
    )


async def load_open_positions_as_of(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
):
    """Projeta somente posições abertas até ``target_date``."""

    timelines = await load_position_timelines_as_of(db, portfolio_id, target_date)
    return {
        ticker: item
        for ticker, item in timelines.items()
        if item[0].quantity > 0
    }


async def load_realized_pnl_as_of(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, float]:
    """Retorna PnL realizado por ticker até ``target_date``."""

    timelines = await load_position_timelines_as_of(db, portfolio_id, target_date)
    return {
        ticker: float(projection.realized_pnl)
        for ticker, (projection, _, _) in timelines.items()
    }
