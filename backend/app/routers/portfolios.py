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


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PositionItem(BaseModel):
    ticker:         str
    asset_type:     str
    asset_label:    str
    quantity:       float
    avg_price:      float
    total_invested: float
    logo_url:       Optional[str]   = None
    # Campos nullable: None quando cotacao indisponivel
    current_price:  Optional[float] = None
    current_value:  Optional[float] = None
    result_abs:     Optional[float] = None
    result_pct:     Optional[float] = None


class SummaryResponse(BaseModel):
    total_invested:           float
    # Campos nullable: None quando nenhuma posicao tem cotacao disponivel
    total_current:            Optional[float] = None
    result_abs:               Optional[float] = None
    result_pct:               Optional[float] = None
    positions_count:          int
    total_patrimonio:         Optional[float] = None
    total_investido:          float
    lucro_total:              Optional[float] = None
    variacao_valor:           Optional[float] = None
    variacao_percentual:      Optional[float] = None
    rentabilidade_total:      Optional[float] = None
    dividendos_recebidos_12m: float
    total_proventos:          float


class EquityHistoryPoint(BaseModel):
    month:    str
    value:    float
    invested: float


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

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
    return MessageResponse(message='Carteira excluida com sucesso')


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get('/{portfolio_id}/summary', response_model=SummaryResponse)
async def portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(db, portfolio_id, current_user.id)

    items          = await calc_positions(db, portfolio_id)
    total_invested = round(sum(i['total_invested'] for i in items), 2)

    # current_value pode ser None para ativos sem cotacao;
    # total_current so e calculado se ao menos uma posicao tem cotacao.
    values_with_quote = [i['current_value'] for i in items if i['current_value'] is not None]
    total_current     = round(sum(values_with_quote), 2) if values_with_quote else None

    if total_current is not None and total_invested > 0:
        # Usa apenas o investido correspondente aos ativos com cotacao
        invested_with_quote = round(
            sum(i['total_invested'] for i in items if i['current_value'] is not None), 2
        )
        result_abs = round(total_current - invested_with_quote, 2)
        result_pct = round((result_abs / invested_with_quote * 100) if invested_with_quote > 0 else 0.0, 4)
    else:
        result_abs = None
        result_pct = None

    cutoff          = date.today() - timedelta(days=365)
    proventos_12m   = await sum_dividends(db, portfolio_id, cutoff=cutoff)
    total_proventos = await sum_dividends(db, portfolio_id)

    return SummaryResponse(
        total_invested           = total_invested,
        total_current            = total_current,
        result_abs               = result_abs,
        result_pct               = result_pct,
        positions_count          = len(items),
        total_patrimonio         = total_current,
        total_investido          = total_invested,
        lucro_total              = result_abs,
        variacao_valor           = result_abs,
        variacao_percentual      = result_pct,
        rentabilidade_total      = result_pct,
        dividendos_recebidos_12m = proventos_12m,
        total_proventos          = total_proventos,
    )


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

@router.get('/{portfolio_id}/positions', response_model=list[PositionItem])
async def portfolio_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(db, portfolio_id, current_user.id)
    return await calc_positions(db, portfolio_id)


# ---------------------------------------------------------------------------
# Equity History
# ---------------------------------------------------------------------------

@router.get('/{portfolio_id}/equity-history', response_model=list[EquityHistoryPoint])
async def portfolio_equity_history(
    portfolio_id: int,
    period: str = Query(default='12m', description="Periodo: 6m | 12m | 24m | all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evolucao patrimonial mensal.
    Hoje ambas as series (value e invested) usam capital aportado liquido.
    Na Sprint 8 (historico patrimonial), 'value' sera atualizado para valor de mercado.
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
    rows   = result.fetchall()

    if not rows:
        return []

    points: list[EquityHistoryPoint] = []
    accumulated = 0.0
    for row in rows:
        month, net_invested = row
        accumulated += float(net_invested or 0)
        points.append(EquityHistoryPoint(
            month    = month,
            value    = round(accumulated, 2),
            invested = round(accumulated, 2),
        ))

    return points
