from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.performance_service import get_portfolio_performance
from app.services.portfolio_snapshot_read_service import (
    get_enriched_daily_evolution,
    get_enriched_monthly_evolution,
)
from app.services.portfolio_snapshot_twr_service import backfill_snapshots_with_returns
from app.services.portfolio_class_snapshot_service import rebuild_class_snapshots
from app.services.portfolio_class_snapshot_read_service import (
    get_class_twr_availability,
    get_daily_class_evolution,
    get_monthly_class_evolution,
)
from app.models.portfolio import Portfolio
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["performance"])


async def _assert_portfolio_owner(db: AsyncSession, portfolio_id: int, user_id: int) -> None:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
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
    days: int = Query(default=365, ge=0, le=3650, description="Dias para buscar; 0 retorna todo o histórico"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_enriched_daily_evolution(db, portfolio_id, days=days)


@router.get("/{portfolio_id}/evolution/monthly")
async def evolution_monthly(
    portfolio_id: int,
    months: int = Query(default=12, ge=0, le=120, description="Meses para buscar; 0 retorna todo o histórico"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_enriched_monthly_evolution(db, portfolio_id, months=months)


@router.get("/{portfolio_id}/classes/availability")
async def class_performance_availability(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_class_twr_availability(db, portfolio_id)


@router.get("/{portfolio_id}/classes/{asset_type}/evolution/daily")
async def class_evolution_daily(
    portfolio_id: int,
    asset_type: str,
    days: int = Query(default=365, ge=0, le=3650),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_daily_class_evolution(db, portfolio_id, asset_type, days=days)


@router.get("/{portfolio_id}/classes/{asset_type}/evolution/monthly")
async def class_evolution_monthly(
    portfolio_id: int,
    asset_type: str,
    months: int = Query(default=12, ge=0, le=120),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_monthly_class_evolution(db, portfolio_id, asset_type, months=months)


@router.post("/{portfolio_id}/evolution/backfill")
async def evolution_backfill(
    portfolio_id: int,
    days_back: int | None = Query(default=None, ge=1, le=3650, description="Dias para backfill. Omitir = desde a primeira transacao"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reconstrói snapshots consolidados e por classe na mesma operação."""
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    consolidated_count = await backfill_snapshots_with_returns(db, portfolio_id, days_back=days_back)
    class_count = await rebuild_class_snapshots(db, portfolio_id, days_back=days_back)
    logger.info(
        "[evolution/backfill-twr] portfolio=%s user=%s consolidated=%s classes=%s",
        portfolio_id,
        current_user.id,
        consolidated_count,
        class_count,
    )
    return {
        "snapshots_processed": consolidated_count,
        "class_snapshots_processed": class_count,
        "portfolio_id": portfolio_id,
    }
