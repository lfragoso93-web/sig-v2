from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dividend_enums import DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.proventos import (
    ProventosDistributionResponse,
    ProventosListResponse,
    ProventosMonthlyHistoryResponse,
    ProventosSummaryResponse,
)
from app.services.proventos_service import (
    get_distribution,
    get_monthly_history,
    get_summary,
    list_items,
)

router = APIRouter(prefix="/portfolios/{portfolio_id}/proventos", tags=["proventos"])


async def _assert_owner(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id, Portfolio.user_id == user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return portfolio


def _parse_status(status: str | None) -> DividendStatus | None:
    if not status:
        return None
    try:
        return DividendStatus(status.upper())
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Status invalido. Use RECEBIDO ou A_RECEBER."
        )


def _parse_dividend_type(dividend_type: str | None) -> DividendType | None:
    if not dividend_type:
        return None
    try:
        return DividendType(dividend_type.upper())
    except ValueError:
        valid = ", ".join(t.value for t in DividendType)
        raise HTTPException(
            status_code=422, detail=f"Tipo de provento invalido. Use um de: {valid}."
        )


@router.get("/summary", response_model=ProventosSummaryResponse)
async def proventos_summary(
    portfolio_id: int,
    status: str | None = Query(None),
    year: int | None = Query(None),
    asset_type: str | None = Query(None),
    dividend_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owner(portfolio_id, current_user, db)
    return await get_summary(
        db,
        portfolio_id,
        status=_parse_status(status),
        year=year,
        asset_type=asset_type,
        dividend_type=_parse_dividend_type(dividend_type),
    )


@router.get("", response_model=ProventosListResponse)
async def list_proventos(
    portfolio_id: int,
    status: str | None = Query(None),
    year: int | None = Query(None),
    asset_type: str | None = Query(None),
    dividend_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owner(portfolio_id, current_user, db)
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


@router.get(
    "/historico-mensal",
    response_model=list[ProventosMonthlyHistoryResponse],
)
async def proventos_historico_mensal(
    portfolio_id: int,
    status: str | None = Query(None),
    year: int | None = Query(None),
    asset_type: str | None = Query(None),
    dividend_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owner(portfolio_id, current_user, db)
    return await get_monthly_history(
        db,
        portfolio_id,
        status=_parse_status(status),
        year=year,
        asset_type=asset_type,
        dividend_type=_parse_dividend_type(dividend_type),
    )


@router.get(
    "/distribuicao",
    response_model=list[ProventosDistributionResponse],
)
async def proventos_distribuicao(
    portfolio_id: int,
    months: int = Query(12, ge=1, le=120),
    status: str | None = Query(None),
    year: int | None = Query(None),
    asset_type: str | None = Query(None),
    dividend_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_owner(portfolio_id, current_user, db)
    return await get_distribution(
        db,
        portfolio_id,
        months=months,
        status=_parse_status(status),
        year=year,
        asset_type=asset_type,
        dividend_type=_parse_dividend_type(dividend_type),
    )
