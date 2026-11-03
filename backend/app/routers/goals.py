"""
Router de metas financeiras.

Endpoints:
  GET    /portfolios/{portfolio_id}/goals         -> lista metas da carteira
  POST   /portfolios/{portfolio_id}/goals         -> cria meta
  GET    /portfolios/{portfolio_id}/goals/{id}    -> detalhe de uma meta
  PUT    /portfolios/{portfolio_id}/goals/{id}    -> atualiza meta
  DELETE /portfolios/{portfolio_id}/goals/{id}    -> remove meta
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from app.services.portfolio_objectives_access_service import (
    READ_PORTFOLIO_GOALS,
    WRITE_PORTFOLIO_GOALS,
    create_authorized_goal,
    delete_authorized_goal,
    get_authorized_goal,
    get_authorized_goals,
    update_authorized_goal,
)

router = APIRouter(tags=["goals"])


def _access_context(
    portfolio_id: int, user: User, permission: str
) -> PortfolioAccessContext:
    if portfolio_id <= 0:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada ou sem permissao")
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({permission}),
    )


@router.get("/{portfolio_id}/goals", response_model=list[GoalResponse])
async def list_goals_endpoint(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_authorized_goals(
        db, _access_context(portfolio_id, current_user, READ_PORTFOLIO_GOALS)
    )


@router.post("/{portfolio_id}/goals", response_model=GoalResponse, status_code=201)
async def create_goal_endpoint(
    portfolio_id: int,
    body: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.target_value <= 0:
        raise HTTPException(status_code=422, detail="target_value deve ser maior que zero.")
    return await create_authorized_goal(
        db, _access_context(portfolio_id, current_user, WRITE_PORTFOLIO_GOALS), body
    )


@router.get("/{portfolio_id}/goals/{goal_id}", response_model=GoalResponse)
async def get_goal_endpoint(
    portfolio_id: int,
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = await get_authorized_goal(
        db, _access_context(portfolio_id, current_user, READ_PORTFOLIO_GOALS), goal_id
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Meta nao encontrada.")
    return goal


@router.put("/{portfolio_id}/goals/{goal_id}", response_model=GoalResponse)
async def update_goal_endpoint(
    portfolio_id: int,
    goal_id: int,
    body: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.target_value is not None and body.target_value <= 0:
        raise HTTPException(status_code=422, detail="target_value deve ser maior que zero.")
    goal = await update_authorized_goal(
        db, _access_context(portfolio_id, current_user, WRITE_PORTFOLIO_GOALS), goal_id, body
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Meta nao encontrada.")
    return goal


@router.delete("/{portfolio_id}/goals/{goal_id}", status_code=204)
async def delete_goal_endpoint(
    portfolio_id: int,
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    removed = await delete_authorized_goal(
        db, _access_context(portfolio_id, current_user, WRITE_PORTFOLIO_GOALS), goal_id
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Meta nao encontrada.")
