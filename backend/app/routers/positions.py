from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.schemas.position import PositionOut, PortfolioSummary
from app.services.quote_service import update_quotes_for_portfolio

router = APIRouter(prefix="/portfolios/{portfolio_id}/positions", tags=["positions"])


def _get_portfolio(portfolio_id: int, user: User, db: Session) -> Portfolio:
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return p


@router.get("", response_model=List[PositionOut])
async def list_positions(
    portfolio_id: int,
    refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista posicoes consolidadas da carteira.
    ?refresh=true dispara atualizacao de cotacoes via BRAPI antes de retornar.
    """
    _get_portfolio(portfolio_id, current_user, db)

    if refresh:
        await update_quotes_for_portfolio(portfolio_id, db)

    positions = (
        db.query(Position)
        .filter(Position.portfolio_id == portfolio_id)
        .order_by(Position.ticker)
        .all()
    )
    return positions


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    portfolio_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resumo consolidado da carteira:
    total investido, valor atual, rentabilidade %.
    """
    _get_portfolio(portfolio_id, current_user, db)

    if refresh:
        await update_quotes_for_portfolio(portfolio_id, db)

    positions = (
        db.query(Position)
        .filter(Position.portfolio_id == portfolio_id)
        .all()
    )

    total_invested = sum(p.avg_price * p.quantity for p in positions)
    total_current  = sum(
        (p.current_value if p.current_value is not None else p.avg_price * p.quantity)
        for p in positions
    )
    result_abs     = total_current - total_invested
    result_pct     = (result_abs / total_invested * 100) if total_invested > 0 else 0.0

    return PortfolioSummary(
        total_invested=total_invested,
        total_current=total_current,
        result_abs=result_abs,
        result_pct=result_pct,
        positions_count=len(positions),
    )
