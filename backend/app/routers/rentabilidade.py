"""
Rentabilidade router.

Endpoints:
  GET /portfolios/{portfolio_id}/rentabilidade/kpis
  GET /portfolios/{portfolio_id}/rentabilidade/ativos
  GET /portfolios/{portfolio_id}/rentabilidade/classes
  GET /portfolios/{portfolio_id}/rentabilidade/benchmarks/monthly
  GET /portfolios/{portfolio_id}/rentabilidade/reconciliation
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.rentabilidade import RentabilidadeKpisResponse
from app.services.portfolio_performance_access_service import (
    READ_PORTFOLIO_RENTABILIDADE,
    get_authorized_monthly_benchmarks,
    get_authorized_rentabilidade_assets,
    get_authorized_rentabilidade_classes,
    get_authorized_rentabilidade_kpis,
    get_authorized_rentabilidade_reconciliation,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rentabilidade"])


def _access_context(portfolio_id: int, user: User) -> PortfolioAccessContext:
    if portfolio_id <= 0:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada ou sem permissao")
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({READ_PORTFOLIO_RENTABILIDADE}),
    )


@router.get(
    "/{portfolio_id}/rentabilidade/kpis",
    response_model=RentabilidadeKpisResponse,
)
async def rentabilidade_kpis(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs monetários atuais e TWR fechado, com referências independentes."""
    return await get_authorized_rentabilidade_kpis(
        db, _access_context(portfolio_id, current_user)
    )


@router.get("/{portfolio_id}/rentabilidade/ativos")
async def rentabilidade_ativos(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resultado monetário por ativo; percentuais simples não representam TWR."""
    return await get_authorized_rentabilidade_assets(
        db, _access_context(portfolio_id, current_user)
    )


@router.get("/{portfolio_id}/rentabilidade/classes")
async def rentabilidade_classes(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Valuation atual e TWR fechado por classe, quando disponível."""
    return await get_authorized_rentabilidade_classes(
        db, _access_context(portfolio_id, current_user)
    )


@router.get("/{portfolio_id}/rentabilidade/benchmarks/monthly")
async def rentabilidade_benchmarks_monthly(
    portfolio_id: int,
    months: int = Query(default=12, ge=0, le=1200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retornos mensais de benchmarks lidos exclusivamente do banco."""
    return await get_authorized_monthly_benchmarks(
        db, _access_context(portfolio_id, current_user), months=months
    )


@router.get("/{portfolio_id}/rentabilidade/reconciliation")
async def rentabilidade_reconciliation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reconcilia Rentabilidade com summary.v2 e totais canônicos por classe."""
    return await get_authorized_rentabilidade_reconciliation(
        db, _access_context(portfolio_id, current_user)
    )
