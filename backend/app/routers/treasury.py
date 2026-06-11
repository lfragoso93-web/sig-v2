from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.treasury import TreasuryCreate, TreasuryUpdate, TreasuryResponse
from app.services import treasury_service
from app.services.portfolio_service import get_portfolio_by_id

router = APIRouter()


# ---------- helper: valida posse da carteira ---------------------------------

async def _check_portfolio_ownership(
    portfolio_id: int,
    current_user: User,
    db: AsyncSession,
) -> None:
    portfolio = await get_portfolio_by_id(db, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carteira não encontrada.",
        )


# ---------- CRUD endpoints ---------------------------------------------------

@router.get(
    "/portfolios/{portfolio_id}/treasury",
    response_model=list[TreasuryResponse],
    summary="Lista investimentos em Tesouro Direto de uma carteira",
)
async def list_treasury(
    portfolio_id: int,
    only_active: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_portfolio_ownership(portfolio_id, current_user, db)
    investments = await treasury_service.get_treasury_by_portfolio(db, portfolio_id, only_active)
    return await treasury_service.enrich_with_current_prices(investments)


@router.post(
    "/portfolios/{portfolio_id}/treasury",
    response_model=TreasuryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra novo investimento em Tesouro Direto",
)
async def create_treasury(
    portfolio_id: int,
    body: TreasuryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_portfolio_ownership(portfolio_id, current_user, db)
    investment = await treasury_service.create_treasury(
        db, portfolio_id, body.model_dump()
    )
    enriched = await treasury_service.enrich_with_current_prices([investment])
    return enriched[0]


@router.get(
    "/portfolios/{portfolio_id}/treasury/{investment_id}",
    response_model=TreasuryResponse,
    summary="Detalhe de um investimento em Tesouro Direto",
)
async def get_treasury(
    portfolio_id: int,
    investment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_portfolio_ownership(portfolio_id, current_user, db)
    investment = await treasury_service.get_treasury_by_id(db, investment_id, portfolio_id)
    enriched = await treasury_service.enrich_with_current_prices([investment])
    return enriched[0]


@router.patch(
    "/portfolios/{portfolio_id}/treasury/{investment_id}",
    response_model=TreasuryResponse,
    summary="Atualiza investimento em Tesouro Direto",
)
async def update_treasury(
    portfolio_id: int,
    investment_id: int,
    body: TreasuryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_portfolio_ownership(portfolio_id, current_user, db)
    data = body.model_dump(exclude_unset=True)
    investment = await treasury_service.update_treasury(db, investment_id, portfolio_id, data)
    enriched = await treasury_service.enrich_with_current_prices([investment])
    return enriched[0]


@router.delete(
    "/portfolios/{portfolio_id}/treasury/{investment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove investimento em Tesouro Direto",
)
async def delete_treasury(
    portfolio_id: int,
    investment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_portfolio_ownership(portfolio_id, current_user, db)
    await treasury_service.delete_treasury(db, investment_id, portfolio_id)
