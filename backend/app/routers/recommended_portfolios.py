from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.recommended_portfolio import (
    RecommendedPortfolio,
    RecommendedPortfolioSimulationRequest,
    RecommendedPortfolioSimulationResponse,
)
from app.services.recommended_portfolio_service import RecommendedPortfolioService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommended-portfolios"])


@router.get("", response_model=list[RecommendedPortfolio])
async def list_recommended_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RecommendedPortfolio]:
    """Retorna as carteiras recomendadas globais pelas 3 premissas da IA."""
    return await RecommendedPortfolioService.list_recommended_portfolios(db)


@router.get("/{strategy}", response_model=RecommendedPortfolio)
async def get_recommended_portfolio(
    strategy: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendedPortfolio:
    """Retorna o detalhamento analítico da carteira recomendada para a premissa informada."""
    portfolio = await RecommendedPortfolioService.get_recommended_portfolio(strategy, db)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estratégia recomendada '{strategy}' não encontrada. Use 'patrimonio', 'proventos' ou 'performance'.",
        )
    return portfolio


@router.post("/simulate", response_model=RecommendedPortfolioSimulationResponse)
async def simulate_recommended_contribution(
    request: RecommendedPortfolioSimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendedPortfolioSimulationResponse:
    """Simula a distribuição de um aporte entre as classes e ativos recomendados pela IA."""
    if request.total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O valor total a ser aportado deve ser maior que zero.",
        )
    return await RecommendedPortfolioService.simulate_contribution(request, db)
