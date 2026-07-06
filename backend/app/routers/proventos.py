from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dividend import DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.proventos_service import (
    ensure_portfolio_proventos,
    get_distribution,
    get_monthly_history,
    get_summary,
    list_items,
)

router = APIRouter(prefix="/portfolios/{portfolio_id}/proventos", tags=["proventos"])


async def _assert_owner(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return portfolio


async def _prepare_proventos(portfolio_id: int, user: User, db: AsyncSession) -> None:
    await _assert_owner(portfolio_id, user, db)
    await ensure_portfolio_proventos(db, portfolio_id)


def _parse_status(status: Optional[str]) -> Optional[DividendStatus]:
    if not status:
        return None
    try:
        return DividendStatus(status.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail="Status invalido. Use RECEBIDO ou A_RECEBER.")


def _parse_dividend_type(dividend_type: Optional[str]) -> Optional[DividendType]:
    if not dividend_type:
        return None
    try:
        return DividendType(dividend_type.upper())
    except ValueError:
        valid = ", ".join(t.value for t in DividendType)
        raise HTTPException(status_code=422, detail=f"Tipo de provento invalido. Use um de: {valid}.")


@router.get("/summary")
async def proventos_summary(
    portfolio_id: int,
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    dividend_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _prepare_proventos(portfolio_id, current_user, db)
    return await get_summary(
        db,
        portfolio_id,
        status=_parse_status(status),
        year=year,
        asset_type=asset_type,
        dividend_type=_parse_dividend_type(dividend_type),
    )


@router.get("")
async def list_proventos(
    portfolio_id: int,
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    dividend_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _prepare_proventos(portfolio_id, current_user, db)
    return await list_items(
        db,
        portfolio_id,
        status=_parse_status(status),
        year=year,
        asset_type=asset_type,
        dividend_type=_parse_dividend_type(dividend_type),
        page=page,
        page_size=page_size,
    )


@router.get("/historico-mensal")
async def proventos_historico_mensal(
    portfolio_id: int,
    status: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    dividend_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _prepare_proventos(portfolio_id, current_user, db)
    return await get_monthly_history(
        db,
        portfolio_id,
        status=_parse_status(status),
        asset_type=asset_type,
        dividend_type=_parse_dividend_type(dividend_type),
    )


@router.get("/distribuicao")
async def proventos_distribuicao(
    portfolio_id: int,
    months: int = Query(12, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _prepare_proventos(portfolio_id, current_user, db)
    return await get_distribution(db, portfolio_id, months=months)
