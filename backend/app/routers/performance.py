from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio_evolution import (
    PortfolioClassAvailabilityResponse,
    PortfolioClassDailyEvolutionResponse,
    PortfolioClassMonthlyEvolutionResponse,
    PortfolioClassReconciliationResponse,
    PortfolioDailyEvolutionResponse,
    PortfolioMonthlyEvolutionResponse,
)
from app.services.performance_service import get_portfolio_performance
from app.services.portfolio_class_reconciliation_service import (
    reconcile_latest_class_snapshots,
)
from app.services.portfolio_class_snapshot_read_service import (
    get_class_twr_availability,
    get_daily_class_evolution,
    get_monthly_class_evolution,
)
from app.services.portfolio_snapshot_read_service import (
    get_enriched_daily_evolution,
    get_enriched_monthly_evolution,
)

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


@router.get(
    "/{portfolio_id}/evolution/daily",
    response_model=list[PortfolioDailyEvolutionResponse],
)
async def evolution_daily(
    portfolio_id: int,
    days: int = Query(
        default=365,
        ge=0,
        le=3650,
        description="Dias para buscar; 0 retorna todo o histórico",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_enriched_daily_evolution(db, portfolio_id, days=days)


@router.get(
    "/{portfolio_id}/evolution/monthly",
    response_model=list[PortfolioMonthlyEvolutionResponse],
)
async def evolution_monthly(
    portfolio_id: int,
    months: int = Query(
        default=12,
        ge=0,
        le=120,
        description="Meses para buscar; 0 retorna todo o histórico",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_enriched_monthly_evolution(db, portfolio_id, months=months)


@router.get(
    "/{portfolio_id}/classes/availability",
    response_model=list[PortfolioClassAvailabilityResponse],
)
async def class_performance_availability(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_class_twr_availability(db, portfolio_id)


@router.get(
    "/{portfolio_id}/classes/reconciliation/latest",
    response_model=PortfolioClassReconciliationResponse,
)
async def class_performance_reconciliation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await reconcile_latest_class_snapshots(db, portfolio_id)


@router.get(
    "/{portfolio_id}/classes/{asset_type}/evolution/daily",
    response_model=list[PortfolioClassDailyEvolutionResponse],
)
async def class_evolution_daily(
    portfolio_id: int,
    asset_type: str,
    days: int = Query(default=365, ge=0, le=3650),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_daily_class_evolution(db, portfolio_id, asset_type, days=days)


@router.get(
    "/{portfolio_id}/classes/{asset_type}/evolution/monthly",
    response_model=list[PortfolioClassMonthlyEvolutionResponse],
)
async def class_evolution_monthly(
    portfolio_id: int,
    asset_type: str,
    months: int = Query(default=12, ge=0, le=120),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    return await get_monthly_class_evolution(db, portfolio_id, asset_type, months=months)
