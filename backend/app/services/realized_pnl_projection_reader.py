"""Leitura read-only do resultado realizado projetado por carteira."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.portfolio_service import normalize_type
from app.services.snapshot_position_projection import project_transaction_timelines

_RENDA_FIXA_TYPE = "RENDA_FIXA"


async def load_realized_pnl_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, float]:
    """Projeta PnL realizado sem reconstruir posição com regra paralela."""

    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
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
    timelines = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=datetime.now(UTC).date(),
    )
    return {
        ticker: float(projection.realized_pnl)
        for ticker, (projection, _, _) in timelines.items()
    }
