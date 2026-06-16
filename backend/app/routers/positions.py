from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from decimal import Decimal

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.schemas.position import PositionOut, PortfolioSummary
from app.services.quote_service import update_quotes_for_portfolio

router = APIRouter(prefix="/portfolios/{portfolio_id}/positions", tags=["positions"])


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


@router.get("", response_model=List[PositionOut])
async def list_positions(
    portfolio_id: int,
    refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista posicoes consolidadas da carteira.
    ?refresh=true dispara atualizacao de cotacoes via BRAPI antes de retornar.
    """
    await _get_portfolio(portfolio_id, current_user, db)

    if refresh:
        await update_quotes_for_portfolio(portfolio_id, db)

    result = await db.execute(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .order_by(Position.ticker)
    )
    return result.scalars().all()


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    portfolio_id: int,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resumo consolidado da carteira:
    total investido, valor atual, rentabilidade %.
    """
    portfolio = await _get_portfolio(portfolio_id, current_user, db)

    if refresh:
        await update_quotes_for_portfolio(portfolio_id, db)

    result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()

    total_invested = sum(
        (p.average_price or Decimal(0)) * (p.quantity or Decimal(0))
        for p in positions
    )
    current_value = sum(
        p.current_value if p.current_value is not None
        else (p.average_price or Decimal(0)) * (p.quantity or Decimal(0))
        for p in positions
    )
    total_return = current_value - total_invested
    total_return_pct = (
        (total_return / total_invested * 100) if total_invested > 0 else Decimal(0)
    )
    realized_profit = sum(
        p.realized_profit or Decimal(0) for p in positions
    )

    return PortfolioSummary(
        portfolio_id=portfolio.id,
        portfolio_name=portfolio.name,
        total_invested=total_invested,
        current_value=current_value,
        total_return=total_return,
        total_return_pct=total_return_pct,
        realized_profit=realized_profit,
        positions_count=len(positions),
        positions=positions,
    )
