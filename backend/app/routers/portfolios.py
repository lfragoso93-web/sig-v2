from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from app.schemas.auth import MessageResponse
from app.schemas.position import PortfolioSummary
from app.services.portfolio_service import (
    list_portfolios, create_portfolio, update_portfolio, delete_portfolio
)
from app.services.position_service import get_portfolio_summary

router = APIRouter()


@router.get("/", response_model=list[PortfolioResponse])
async def list_my_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as carteiras do usuário autenticado."""
    return await list_portfolios(db, current_user.id)


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_my_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria nova carteira para o usuário autenticado."""
    return await create_portfolio(db, current_user.id, data)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.portfolio_service import get_portfolio as _get
    return await _get(db, portfolio_id, current_user.id)


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_my_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_portfolio(db, portfolio_id, current_user.id, data)


@router.delete("/{portfolio_id}", response_model=MessageResponse)
async def delete_my_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_portfolio(db, portfolio_id, current_user.id)
    return MessageResponse(message="Carteira excluída com sucesso")


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumo completo da carteira com preço médio, valor atual e rentabilidade."""
    return await get_portfolio_summary(db, portfolio_id, current_user.id)
