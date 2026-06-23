from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.performance_service import get_portfolio_performance
from app.services.portfolio_snapshot_service import (
    get_daily_evolution,
    get_monthly_evolution,
    backfill_snapshots,
)
from app.models.portfolio import Portfolio
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["performance"])


async def _assert_portfolio_owner(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> None:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")


@router.get("/{portfolio_id}/performance")
async def portfolio_performance(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_portfolio_performance(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/evolution/daily")
async def evolution_daily(
    portfolio_id: int,
    days: int = Query(default=365, ge=7, le=3650, description="Numero de dias para buscar (7-3650)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna evolucao diaria do patrimonio com base nos snapshots.
    Cada ponto tem: date, market_value, cost_basis, invested_total,
    unrealized_pnl, realized_pnl, total_pnl, return_pct.
    """
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    data = await get_daily_evolution(db, portfolio_id, days=days)
    return data


@router.get("/{portfolio_id}/evolution/monthly")
async def evolution_monthly(
    portfolio_id: int,
    months: int = Query(default=12, ge=1, le=120, description="Numero de meses para buscar (1-120)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna evolucao mensal do patrimonio (ultimo snapshot de cada mes).
    Cada ponto tem: date, period, value/market_value, invested/invested_total,
    unrealized_pnl, realized_pnl, total_pnl, return_pct.
    """
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    data = await get_monthly_evolution(db, portfolio_id, months=months)
    return data


@router.post("/{portfolio_id}/evolution/backfill")
async def evolution_backfill(
    portfolio_id: int,
    days_back: int = Query(default=None, ge=1, le=3650, description="Dias para backfill. Omitir = desde a primeira transacao"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recalcula snapshots historicos para a carteira.
    Pode demorar alguns segundos para carteiras com historico longo.
    """
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    count = await backfill_snapshots(db, portfolio_id, days_back=days_back)
    logger.info(
        "[evolution/backfill] portfolio=%s user=%s snapshots=%s",
        portfolio_id, current_user.id, count,
    )
    return {"snapshots_processed": count, "portfolio_id": portfolio_id}
