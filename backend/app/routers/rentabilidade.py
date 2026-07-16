"""
Rentabilidade router.

Endpoints:
  GET /portfolios/{portfolio_id}/rentabilidade/kpis
  GET /portfolios/{portfolio_id}/rentabilidade/ativos
  GET /portfolios/{portfolio_id}/rentabilidade/classes
  GET /portfolios/{portfolio_id}/rentabilidade/benchmarks/monthly
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.services.rentabilidade_kpi_service import get_rentabilidade_kpis
from app.services.rentabilidade_service import get_rentabilidade_por_ativo
from app.services.rentabilidade_class_service import get_canonical_class_performance
from app.services.rentabilidade_benchmark_service import get_persisted_monthly_benchmarks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rentabilidade"])


async def _assert_owner(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> None:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Carteira não encontrada.")


@router.get("/{portfolio_id}/rentabilidade/kpis")
async def rentabilidade_kpis(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs atuais canônicos combinados com métricas históricas de retorno."""
    await _assert_owner(db, portfolio_id, current_user.id)
    return await get_rentabilidade_kpis(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/rentabilidade/ativos")
async def rentabilidade_ativos(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resultado monetário por ativo; percentuais simples não representam TWR."""
    await _assert_owner(db, portfolio_id, current_user.id)
    return await get_rentabilidade_por_ativo(db, portfolio_id)


@router.get("/{portfolio_id}/rentabilidade/classes")
async def rentabilidade_classes(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Valuation intradiário e TWR fechado por classe."""
    await _assert_owner(db, portfolio_id, current_user.id)
    return await get_canonical_class_performance(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/rentabilidade/benchmarks/monthly")
async def rentabilidade_benchmarks_monthly(
    portfolio_id: int,
    months: int = Query(default=12, ge=0, le=1200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retornos mensais de benchmarks lidos exclusivamente do banco."""
    await _assert_owner(db, portfolio_id, current_user.id)
    return await get_persisted_monthly_benchmarks(db, months=months)
