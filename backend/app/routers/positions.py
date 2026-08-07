"""
Router de posicoes — leitura financeira exclusivamente DB-first.

Os calculos permanecem delegados ao portfolio_service e usam schemas alinhados
com o contrato atual (AssetGroupOut e PortfolioSummary). Atualizacao de cotacoes
nao pertence a requests de leitura de posicao/resumo.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.position import AssetGroupOut, PortfolioSummary
from app.services.portfolio_service import (
    get_portfolio_positions,
    get_portfolio_summary,
)

router = APIRouter(tags=["positions"])


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return portfolio


@router.get("/{portfolio_id}/positions", response_model=List[AssetGroupOut])
async def list_positions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista posicoes agrupadas usando somente dados persistidos."""
    await _get_portfolio(portfolio_id, current_user, db)
    return await get_portfolio_positions(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/positions/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o resumo consolidado usando somente dados persistidos."""
    await _get_portfolio(portfolio_id, current_user, db)
    return await get_portfolio_summary(db, portfolio_id, current_user.id)
