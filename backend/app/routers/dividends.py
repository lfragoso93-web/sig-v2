"""
Router de proventos.
Todos os endpoints sao async e usam o novo modelo AssetDividend.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.dividend_service import (
    get_dividend_summary,
    list_dividends,
    update_dividend_status,
)

router = APIRouter()


# -- helper -------------------------------------------------------------------

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


# -- endpoints ----------------------------------------------------------------

@router.get("/portfolios/{portfolio_id}/dividends")
async def list_portfolio_dividends(
    portfolio_id: int,
    asset_id: Optional[int] = Query(None, description="Filtrar por ativo"),
    year: Optional[int] = Query(None, description="Filtrar por ano"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista proventos de uma carteira com paginacao e filtros."""
    await _get_portfolio(portfolio_id, current_user, db)
    dividends, total = await list_dividends(
        db, portfolio_id, asset_id=asset_id, year=year, page=page, page_size=page_size
    )

    items = []
    for d in dividends:
        ad: AssetDividend = d.asset_dividend
        items.append({
            "id":             d.id,
            "portfolio_id":   d.portfolio_id,
            "asset_id":       ad.asset_id,
            "ticker":         ad.asset.ticker if ad.asset else None,
            "dividend_type":  ad.dividend_type,
            "ex_date":        ad.ex_date,
            "payment_date":   ad.payment_date,
            "value_per_unit": float(ad.value_per_unit),
            "quantity":       d.quantity,
            "total_value":    float(d.total_value) if d.total_value else None,
            "net_value":      float(d.net_value)   if d.net_value   else None,
            "status":         d.status,
            "source":         ad.source,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/portfolios/{portfolio_id}/dividends/summary")
async def portfolio_dividend_summary(
    portfolio_id: int,
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Totais de proventos agrupados por tipo para a carteira."""
    await _get_portfolio(portfolio_id, current_user, db)
    return await get_dividend_summary(db, portfolio_id, year=year)


@router.patch("/portfolios/{portfolio_id}/dividends/{dividend_id}")
async def patch_dividend_status(
    portfolio_id: int,
    dividend_id: int,
    status_value: DividendStatus = Query(..., alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza status de um provento manualmente (RECEBIDO / A_RECEBER)."""
    await _get_portfolio(portfolio_id, current_user, db)
    div = await update_dividend_status(db, portfolio_id, dividend_id, status_value)
    if not div:
        raise HTTPException(status_code=404, detail="Provento nao encontrado.")
    return {"id": div.id, "status": div.status}
