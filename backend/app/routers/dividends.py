from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.dividend import DividendCreate, DividendResponse, DividendSummaryResponse
from app.schemas.pagination import PaginatedResponse
from app.services.dividend_service import (
    create_dividend_manual, list_dividends, get_dividend_summary
)
from app.services.portfolio_service import get_portfolio
from typing import Optional
import math

router = APIRouter()


@router.get("/{portfolio_id}/dividends", response_model=PaginatedResponse[DividendResponse])
async def list_portfolio_dividends(
    portfolio_id: int,
    asset_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista proventos recebidos. Filtravel por ativo e ano."""
    await get_portfolio(db, portfolio_id, current_user.id)
    dividends, total = await list_dividends(db, portfolio_id, asset_id, year, page, page_size)
    return PaginatedResponse(
        items=dividends,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post(
    "/{portfolio_id}/dividends",
    response_model=DividendResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_dividend_manual(
    portfolio_id: int,
    data: DividendCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lancamento manual de provento (para ativos sem cobertura BRAPI)."""
    await get_portfolio(db, portfolio_id, current_user.id)
    return await create_dividend_manual(db, portfolio_id, data)


@router.get(
    "/{portfolio_id}/dividends/summary",
    response_model=DividendSummaryResponse,
)
async def dividend_summary(
    portfolio_id: int,
    year: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resumo de proventos por tipo com total geral. Filtravel por ano."""
    await get_portfolio(db, portfolio_id, current_user.id)
    return await get_dividend_summary(db, portfolio_id, year)
