"""
Router de posicoes — leitura financeira exclusivamente DB-first.

Os calculos permanecem delegados ao portfolio_service e usam schemas alinhados
com o contrato atual (AssetGroupOut e PortfolioSummary). Atualizacao de cotacoes
nao pertence a requests de leitura de posicao/resumo.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.position import AssetGroupOut, PortfolioSummary
from app.services.portfolio_positions_access_service import (
    READ_PORTFOLIO_POSITIONS,
    get_authorized_legacy_positions,
    get_authorized_legacy_summary,
)

router = APIRouter(tags=["positions"])


def _access_context(portfolio_id: int, user: User) -> PortfolioAccessContext:
    if portfolio_id <= 0:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada ou sem permissao")
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({READ_PORTFOLIO_POSITIONS}),
    )


@router.get("/{portfolio_id}/positions", response_model=List[AssetGroupOut])
async def list_positions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista posicoes agrupadas usando somente dados persistidos."""
    return await get_authorized_legacy_positions(db, _access_context(portfolio_id, current_user))


@router.get("/{portfolio_id}/positions/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o resumo consolidado usando somente dados persistidos."""
    return await get_authorized_legacy_summary(db, _access_context(portfolio_id, current_user))
