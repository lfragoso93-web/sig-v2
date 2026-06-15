"""
Router de proventos da carteira.
Endpoints:
  GET  /portfolios/{id}/proventos/summary          -> totais recebido/a-receber/12m
  GET  /portfolios/{id}/proventos                  -> lista paginada (recebidos + futuros)
  GET  /portfolios/{id}/proventos/historico-mensal -> historico por ano/mes
  GET  /portfolios/{id}/proventos/distribuicao     -> % por ativo (ultimos N meses)

Todos async, AsyncSession, sem schemas externos.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dividend import DividendStatus
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.proventos_service import (
    get_distribution,
    get_monthly_history,
    get_summary,
    list_items,
)

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/proventos",
    tags=["proventos"],
)


# -- helper -------------------------------------------------------------------

async def _assert_owner(
    portfolio_id: int,
    user: User,
    db: AsyncSession,
) -> Portfolio:
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


# -- endpoints ----------------------------------------------------------------

@router.get("/summary")
async def proventos_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Totais da carteira:
      - total_recebido: soma de net_value ja recebidos
      - total_a_receber: soma de net_value futuros
      - total_12m: recebido nos ultimos 12 meses
      - media_mensal_12m: total_12m / 12
    """
    await _assert_owner(portfolio_id, current_user, db)
    return await get_summary(db, portfolio_id)


@router.get("")
async def list_proventos(
    portfolio_id: int,
    status: Optional[str] = Query(
        None,
        description="Filtrar por status: RECEBIDO | A_RECEBER",
    ),
    year: Optional[int] = Query(None, description="Filtrar por ano da ex_date"),
    asset_type: Optional[str] = Query(None, description="Filtrar por tipo de ativo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista proventos da carteira com filtros.
    Retorna recebidos E futuros (sem filtro de status).
    Cada item inclui: ticker, value_per_unit, quantity, total_value,
    net_value, ex_date, payment_date, status.
    """
    await _assert_owner(portfolio_id, current_user, db)

    status_enum: Optional[DividendStatus] = None
    if status:
        try:
            status_enum = DividendStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Status invalido: '{status}'. Use RECEBIDO ou A_RECEBER.",
            )

    return await list_items(
        db,
        portfolio_id,
        status=status_enum,
        year=year,
        asset_type=asset_type,
        page=page,
        page_size=page_size,
    )


@router.get("/historico-mensal")
async def proventos_historico_mensal(
    portfolio_id: int,
    status: Optional[str] = Query(None, description="RECEBIDO | A_RECEBER"),
    asset_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Historico mensal agrupado por ano.
    Cada entrada: { year, months: [v_jan..v_dez], total, media }
    Meses sem provento retornam null.
    """
    await _assert_owner(portfolio_id, current_user, db)

    status_enum: Optional[DividendStatus] = None
    if status:
        try:
            status_enum = DividendStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Status invalido: '{status}'. Use RECEBIDO ou A_RECEBER.",
            )

    return await get_monthly_history(
        db, portfolio_id, status=status_enum, asset_type=asset_type
    )


@router.get("/distribuicao")
async def proventos_distribuicao(
    portfolio_id: int,
    months: int = Query(12, ge=1, le=120, description="Periodo em meses (padrao 12)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Distribuicao percentual por ativo nos ultimos N meses.
    Cada entrada: { ticker, asset_type, total, percentage }
    """
    await _assert_owner(portfolio_id, current_user, db)
    return await get_distribution(db, portfolio_id, months=months)
