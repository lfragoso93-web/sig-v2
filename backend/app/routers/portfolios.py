from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from app.schemas.auth import MessageResponse
from app.services.portfolio_service import (
    list_portfolios, create_portfolio, update_portfolio, delete_portfolio
)

router = APIRouter()


# ── Schemas inline para summary/positions ──────────────────────────────
class PositionItem(BaseModel):
    ticker:        str
    asset_type:    str
    quantity:      float
    avg_price:     float
    total_invested: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    result_abs:    Optional[float] = None
    result_pct:    Optional[float] = None


class SummaryResponse(BaseModel):
    total_invested:          float
    total_current:           float
    result_abs:              float
    result_pct:              float
    positions_count:         int
    # aliases para os hooks do frontend
    total_patrimonio:        float
    total_investido:         float
    lucro_total:             float
    variacao_valor:          float
    variacao_percentual:     float
    rentabilidade_total:     float
    dividendos_recebidos_12m: float
    total_proventos:         float


# ── Helper: calcula posições agregadas das transactions ────────────────
async def _calc_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id
        ).order_by(Transaction.date)
    )
    txs = result.scalars().all()

    # Agrupa por (ticker, asset_type)
    pos: dict[tuple, dict] = {}
    for tx in txs:
        key = (tx.ticker, tx.asset_type)
        if key not in pos:
            pos[key] = {'qty': 0.0, 'total_cost': 0.0, 'ticker': tx.ticker, 'asset_type': tx.asset_type}
        p = pos[key]
        if tx.operation == OperationType.buy:
            p['total_cost'] += tx.quantity * tx.price + (tx.fees or 0)
            p['qty']        += tx.quantity
        else:  # sell
            if p['qty'] > 0:
                avg = p['total_cost'] / p['qty']
                p['total_cost'] -= avg * tx.quantity
            p['qty'] -= tx.quantity

    items = []
    for p in pos.values():
        if p['qty'] > 1e-9:
            avg = p['total_cost'] / p['qty'] if p['qty'] > 0 else 0
            items.append({
                'ticker':        p['ticker'],
                'asset_type':    p['asset_type'],
                'quantity':      round(p['qty'], 8),
                'avg_price':     round(avg, 6),
                'total_invested': round(p['total_cost'], 2),
                'current_price': None,
                'current_value': None,
                'result_abs':    None,
                'result_pct':    None,
            })
    return items


# ── Rotas ───────────────────────────────────────────────────────────────

@router.get("/", response_model=list[PortfolioResponse])
async def list_my_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_portfolios(db, current_user.id)


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_my_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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


@router.get("/{portfolio_id}/summary", response_model=SummaryResponse)
async def portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumo calculado direto das transactions — sem depender de portfolio_positions."""
    from fastapi import HTTPException
    p_res = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    if not p_res.scalar_one_or_none():
        raise HTTPException(404, "Carteira não encontrada")

    items = await _calc_positions(db, portfolio_id)
    total_invested = sum(i['total_invested'] for i in items)
    total_current  = total_invested  # sem cotação real por ora
    result_abs     = total_current - total_invested
    result_pct     = (result_abs / total_invested * 100) if total_invested > 0 else 0.0

    return SummaryResponse(
        total_invested          = round(total_invested, 2),
        total_current           = round(total_current,  2),
        result_abs              = round(result_abs,     2),
        result_pct              = round(result_pct,     4),
        positions_count         = len(items),
        total_patrimonio        = round(total_current,  2),
        total_investido         = round(total_invested, 2),
        lucro_total             = round(result_abs,     2),
        variacao_valor          = round(result_abs,     2),
        variacao_percentual     = round(result_pct,     4),
        rentabilidade_total     = round(result_pct,     4),
        dividendos_recebidos_12m = 0.0,
        total_proventos         = 0.0,
    )


@router.get("/{portfolio_id}/positions", response_model=list[PositionItem])
async def portfolio_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Posições calculadas direto das transactions."""
    from fastapi import HTTPException
    p_res = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    if not p_res.scalar_one_or_none():
        raise HTTPException(404, "Carteira não encontrada")

    return await _calc_positions(db, portfolio_id)
