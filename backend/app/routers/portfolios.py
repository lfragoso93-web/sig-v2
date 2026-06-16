from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from app.services.portfolio_service import (
    create_portfolio,
    list_portfolios,
    get_portfolio,
    update_portfolio,
    delete_portfolio,
    get_portfolio_summary,
    get_portfolio_positions,
    get_asset_distribution,
    get_patrimonio_history,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/", response_model=list[PortfolioResponse])
async def list_user_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_portfolios(db, current_user.id)


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_user_portfolio(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_portfolio(db, current_user.id, data)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_user_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio(db, portfolio_id, current_user.id)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_user_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_portfolio(db, portfolio_id, current_user.id, data)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await delete_portfolio(db, portfolio_id, current_user.id)
    return None


@router.get("/{portfolio_id}/summary")
async def portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio_summary(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/positions")
async def portfolio_positions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio_positions(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/asset-distribution")
async def asset_distribution(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_asset_distribution(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/patrimonio-history")
async def patrimonio_history(
    portfolio_id: int,
    months: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_patrimonio_history(db, portfolio_id, current_user.id, months)
