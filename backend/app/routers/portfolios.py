from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import date, timedelta
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from app.schemas.auth import MessageResponse
from app.services.portfolio_service import (
    list_portfolios,
    create_portfolio,
    update_portfolio,
    delete_portfolio,
    get_portfolio as _get_portfolio,
    calc_positions,
    sum_dividends,
)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────
class PositionItem(BaseModel):
    ticker:         str
    asset_type:     str
    asset_label:    str
    quantity:       float
    avg_price:      float
    total_invested: float
    logo_url:       Optional[str] = None
    current_price:  Optional[float]
    current_value:  float
    result_abs:     float
    result_pct:     float


class SummaryResponse(BaseModel):
    total_invested:           float
    total_current:            float
    result_abs:               float
    result_pct:               float
    positions_count:          int
    total_patrimonio:         float
    total_investido:          float
    lucro_total:              float
    variacao_valor:           float
    variacao_percentual:      float
    rentabilidade_total:      float
    dividendos_recebidos_12m: float
    total_proventos:          float


class EquityHistoryPoint(BaseModel):
    month:    str    # formato YYYY-MM
    value:    float  # valor atual acumulado (capital investido)
    invested: float  # capital aportado acumulado (custo)


# ── CRUD ──────────────────────────────────────────────────────────────────────────────

@router.get('/', response_model=list[PortfolioResponse])
async def list_my_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_portfolios(db, current_user.id)


@router.post('/', response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_my_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_portfolio(db, current_user.id, data)


@router.get('/{portfolio_id}', response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_portfolio(db, portfolio_id, current_user.id)


@router.put('/{portfolio_id}', response_model=PortfolioResponse)
async def update_my_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_portfolio(db, portfolio_id, current_user.id, data)


@router.delete('/{portfolio_id}', response_model=MessageResponse)
async def delete_my_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_portfolio(db, portfolio_id, current_user.id)
    return MessageResponse(message='Carteira excluída com sucesso')


# ── Summary ──────────────────────────────────────────────────────────────────────────

@router.get('/{portfolio_id}/summary', response_model=SummaryResponse)
async def portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(db, portfolio_id, current_user.id)

    items          = await calc_positions(db, portfolio_id)
    total_invested = sum(i['total_invested'] for i in items)
    total_current  = sum(i['current_value']  for i in items)
    result_abs     = round(total_current - total_invested, 2)
    result_pct     = round((result_abs / total_invested * 100) if total_invested > 0 else 0.0, 4)

    cutoff          = date.today() - timedelta(days=365)
    proventos_12m   = await sum_dividends(db, portfolio_id, cutoff=cutoff)
    total_proventos = await sum_dividends(db, portfolio_id)

    return SummaryResponse(
        total_invested           = round(total_invested, 2),
        total_current            = round(total_current,  2),
        result_abs               = result_abs,
        result_pct               = result_pct,
        positions_count          = len(items),
        total_patrimonio         = round(total_current,  2),
        total_investido          = round(total_invested, 2),
        lucro_total              = result_abs,
        variacao_valor           = result_abs,
        variacao_percentual      = result_pct,
        rentabilidade_total      = result_pct,
        dividendos_recebidos_12m = proventos_12m,
        total_proventos          = total_proventos,
    )


# ── Positions ────────────────────────────────────────────────────────────────────────

@router.get('/{portfolio_id}/positions', response_model=list[PositionItem])
async def portfolio_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(db, portfolio_id, current_user.id)
    return await calc_positions(db, portfolio_id)


# ── Equity History ───────────────────────────────────────────────────────────────────

@router.get('/{portfolio_id}/equity-history', response_model=list[EquityHistoryPoint])
async def portfolio_equity_history(
    portfolio_id: int,
    period: str = Query(default='12m', description="Período: 6m | 12m | 24m | all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna a evolução patrimonial por mês com duas séries:
      - value:    capital aportado acumulado (custo histórico)
      - invested: mesmo que value (alias mantido para compatibilidade futura
                  quando integrarmos cotações históricas)

    Hoje ambas as séries usam o capital aportado líquido (compras - vendas).
    Quando tivermos snapshot de preços históricos, 'value' será atualizado
    para refletir o valor de mercado acumulado mois a mês.
    """
    await _get_portfolio(db, portfolio_id, current_user.id)

    today = date.today()
    if period == 'all':
        since = None
    elif period == '6m':
        since = today - timedelta(days=183)
    elif period == '24m':
        since = today - timedelta(days=730)
    else:
        since = today - timedelta(days=365)

    where_clause = "WHERE portfolio_id = :pid"
    params: dict = {'pid': portfolio_id}
    if since:
        where_clause += " AND date >= :since"
        params['since'] = since

    sql = text(f"""
        SELECT
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(
                CASE
                    WHEN operation = 'buy'  THEN quantity * price + COALESCE(fees, 0)
                    WHEN operation = 'sell' THEN -(quantity * price - COALESCE(fees, 0))
                    ELSE 0
                END
            ) AS net_invested
        FROM transactions
        {where_clause}
        GROUP BY month
        ORDER BY month ASC
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    if not rows:
        return []

    points: list[EquityHistoryPoint] = []
    accumulated = 0.0
    for row in rows:
        month, net_invested = row
        accumulated += float(net_invested or 0)
        points.append(EquityHistoryPoint(
            month=month,
            value=round(accumulated, 2),
            invested=round(accumulated, 2),
        ))

    return points
