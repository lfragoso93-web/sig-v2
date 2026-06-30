"""
Router de portfolios.

Endpoints:
  GET  /portfolios/                      - lista portfolios do usuario
  POST /portfolios/                      - cria portfolio
  GET  /portfolios/{id}                  - detalhe
  PUT  /portfolios/{id}                  - atualiza
  DEL  /portfolios/{id}                  - remove
  GET  /portfolios/{id}/distribution     - distribuicao atual por classe
  GET  /portfolios/{id}/class-targets    - metas de alocacao
  POST /portfolios/{id}/class-targets    - upsert meta
  DEL  /portfolios/{id}/class-targets/{asset_type} - remove meta
  GET  /portfolios/{id}/targets-with-current  ← Sprint 5E: alvo vs atual
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services import portfolio_service, class_target_service
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioRead,
    ClassTargetUpsert,
    ClassTargetRead,
    ClassTargetWithCurrent,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])

Db   = Annotated[AsyncSession, Depends(get_db)]
User_ = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _get_portfolio_or_404(portfolio_id: int, user: User, db: AsyncSession):
    portfolio = await portfolio_service.get_portfolio(db, portfolio_id)
    if not portfolio or portfolio.user_id != user.id:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")
    return portfolio


# ---------------------------------------------------------------------------
# CRUD de portfolios
# ---------------------------------------------------------------------------
@router.get("/", response_model=list[PortfolioRead])
async def list_portfolios(db: Db, current_user: User_):
    return await portfolio_service.get_portfolios(db, current_user.id)


@router.post("/", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
async def create_portfolio(payload: PortfolioCreate, db: Db, current_user: User_):
    return await portfolio_service.create_portfolio(db, current_user.id, payload)


@router.get("/{portfolio_id}", response_model=PortfolioRead)
async def get_portfolio(portfolio_id: int, db: Db, current_user: User_):
    return await _get_portfolio_or_404(portfolio_id, current_user, db)


@router.put("/{portfolio_id}", response_model=PortfolioRead)
async def update_portfolio(portfolio_id: int, payload: PortfolioUpdate, db: Db, current_user: User_):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    return await portfolio_service.update_portfolio(db, portfolio_id, payload)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(portfolio_id: int, db: Db, current_user: User_):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    await portfolio_service.delete_portfolio(db, portfolio_id)


# ---------------------------------------------------------------------------
# Distribuicao
# ---------------------------------------------------------------------------
@router.get("/{portfolio_id}/distribution")
async def get_distribution(portfolio_id: int, db: Db, current_user: User_):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    return await portfolio_service.get_asset_distribution(db, portfolio_id)


# ---------------------------------------------------------------------------
# Metas de alocacao por classe
# ---------------------------------------------------------------------------
@router.get("/{portfolio_id}/class-targets", response_model=list[ClassTargetRead])
async def list_class_targets(portfolio_id: int, db: Db, current_user: User_):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    return await class_target_service.get_targets(db, portfolio_id)


@router.post(
    "/{portfolio_id}/class-targets",
    response_model=ClassTargetRead,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_class_target(
    portfolio_id: int,
    payload: ClassTargetUpsert,
    db: Db,
    current_user: User_,
):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    if payload.asset_type not in class_target_service.VALID_ASSET_CLASSES:
        raise HTTPException(
            status_code=422,
            detail=f"Classe '{payload.asset_type}' invalida. "
                   f"Validas: {sorted(class_target_service.VALID_ASSET_CLASSES)}",
        )
    return await class_target_service.upsert_target(
        db, portfolio_id, payload.asset_type, payload.target_pct
    )


@router.delete(
    "/{portfolio_id}/class-targets/{asset_type}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_class_target(
    portfolio_id: int,
    asset_type: str,
    db: Db,
    current_user: User_,
):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    deleted = await class_target_service.delete_target(db, portfolio_id, asset_type)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meta nao encontrada")


# ---------------------------------------------------------------------------
# Sprint 5E: alvo vs atual combinado (inclui BDR)
# ---------------------------------------------------------------------------
@router.get(
    "/{portfolio_id}/targets-with-current",
    response_model=list[ClassTargetWithCurrent],
    summary="Alvo vs. alocacao atual por classe",
    description=(
        "Retorna lista de todas as classes com posicao ativa ou meta configurada, "
        "mostrando percentual atual, meta e delta. BDR e incluso explicitamente "
        "(Sprint 5E - Issue #79)."
    ),
)
async def get_targets_with_current(
    portfolio_id: int,
    db: Db,
    current_user: User_,
):
    await _get_portfolio_or_404(portfolio_id, current_user, db)
    distribution = await portfolio_service.get_asset_distribution(db, portfolio_id)
    return await class_target_service.get_targets_with_current(
        db, portfolio_id, distribution
    )
