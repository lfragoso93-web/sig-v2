"""
Router de posicoes — usa PortfolioPosition (model atual) e delega calculos
para portfolio_service.get_portfolio_positions / get_portfolio_summary.

Os endpoints /{portfolio_id}/positions e /{portfolio_id}/positions/summary
expostos aqui sao aliases para compatibilidade; a fonte de verdade sao os
endpoints equivalentes em portfolios.py.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.services.portfolio_service import (
    get_portfolio_positions,
    get_portfolio_summary,
)
from app.services.quote_service import update_quotes_for_portfolio

router = APIRouter(tags=["positions"])


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return p


@router.get("/{portfolio_id}/positions")
async def list_positions(
    portfolio_id: int,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista posicoes agrupadas por tipo de ativo com preco atual e variacao.
    Delega para portfolio_service.get_portfolio_positions (calc_raw_positions + get_prices).
    """
    await _get_portfolio(portfolio_id, current_user, db)
    if refresh:
        await update_quotes_for_portfolio(portfolio_id, db)
    return await get_portfolio_positions(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/positions/summary")
async def portfolio_summary(
    portfolio_id: int,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resumo consolidado da carteira com patrimonio, retorno e proventos.
    Delega para portfolio_service.get_portfolio_summary.
    """
    await _get_portfolio(portfolio_id, current_user, db)
    if refresh:
        await update_quotes_for_portfolio(portfolio_id, db)
    return await get_portfolio_summary(db, portfolio_id, current_user.id)
