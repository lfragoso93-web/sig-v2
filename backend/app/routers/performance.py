from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.portfolio_evolution import (
    PortfolioClassAvailabilityResponse,
    PortfolioClassDailyEvolutionResponse,
    PortfolioClassMonthlyEvolutionResponse,
    PortfolioClassReconciliationResponse,
    PortfolioDailyEvolutionResponse,
    PortfolioMonthlyEvolutionResponse,
)
from app.services.portfolio_performance_access_service import (
    READ_PORTFOLIO_PERFORMANCE,
    get_authorized_class_availability,
    get_authorized_class_daily_evolution,
    get_authorized_class_monthly_evolution,
    get_authorized_class_reconciliation,
    get_authorized_daily_evolution,
    get_authorized_monthly_evolution,
    get_authorized_performance,
)

router = APIRouter(tags=["performance"])


def _access_context(portfolio_id: int, user: User) -> PortfolioAccessContext:
    if portfolio_id <= 0:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada ou sem permissao")
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({READ_PORTFOLIO_PERFORMANCE}),
    )


@router.get("/{portfolio_id}/performance")
async def portfolio_performance(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_authorized_performance(db, _access_context(portfolio_id, current_user))


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
    return await get_authorized_daily_evolution(
        db, _access_context(portfolio_id, current_user), days=days
    )


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
    return await get_authorized_monthly_evolution(
        db, _access_context(portfolio_id, current_user), months=months
    )


@router.get(
    "/{portfolio_id}/classes/availability",
    response_model=list[PortfolioClassAvailabilityResponse],
)
async def class_performance_availability(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_authorized_class_availability(
        db, _access_context(portfolio_id, current_user)
    )


@router.get(
    "/{portfolio_id}/classes/reconciliation/latest",
    response_model=PortfolioClassReconciliationResponse,
)
async def class_performance_reconciliation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_authorized_class_reconciliation(
        db, _access_context(portfolio_id, current_user)
    )


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
    return await get_authorized_class_daily_evolution(
        db, _access_context(portfolio_id, current_user), asset_type, days=days
    )


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
    return await get_authorized_class_monthly_evolution(
        db, _access_context(portfolio_id, current_user), asset_type, months=months
    )
