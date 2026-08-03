"""Leitura read-only do resultado realizado projetado por carteira."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.portfolio_service import normalize_type
from app.services.position_timeline_projection import CanonicalRealizedDisposal
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
        ticker: float(
            sum(
                (item.realized_pnl_brl for item in projection.realized_disposals),
                start=Decimal(0),
            )
        )
        for ticker, (projection, _, _) in timelines.items()
    }


async def load_realized_disposals(
    db: AsyncSession,
    portfolio_id: int,
    *,
    start_date: date,
    end_date: date,
) -> tuple[CanonicalRealizedDisposal, ...]:
    """Lê baixas canônicas no período preservando histórico para formar custo."""

    if end_date < start_date:
        raise ValueError("end_date deve ser igual ou posterior a start_date")

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= end_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = [
        tx
        for tx in result.scalars().all()
        if normalize_type(tx.asset_type) != _RENDA_FIXA_TYPE
    ]
    if not transactions:
        return ()

    actions_by_ticker = await load_global_corporate_actions_by_ticker(
        db,
        [str(tx.ticker) for tx in transactions],
    )
    timelines = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=end_date,
    )
    return tuple(
        disposal
        for projection, _, _ in timelines.values()
        for disposal in projection.realized_disposals
        if start_date <= disposal.disposal_date <= end_date
    )
