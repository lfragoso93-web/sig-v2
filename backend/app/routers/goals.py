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
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from app.services.goals_service import (
    list_goals,
    get_goal,
    create_goal,
    update_goal,
    delete_goal,
)

router = APIRouter(tags=["goals"])


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


@router.get("/{portfolio_id}/goals", response_model=list[GoalResponse])
async def list_goals_endpoint(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    return await list_goals(db, portfolio_id)


@router.post("/{portfolio_id}/goals", response_model=GoalResponse, status_code=201)
async def create_goal_endpoint(
    portfolio_id: int,
    body: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    if body.target_value <= 0:
        raise HTTPException(status_code=422, detail="target_value deve ser maior que zero.")
    body.portfolio_id = portfolio_id
    return await create_goal(db, body)


@router.get("/{portfolio_id}/goals/{goal_id}", response_model=GoalResponse)
async def get_goal_endpoint(
    portfolio_id: int,
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    goal = await get_goal(db, goal_id, portfolio_id)
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
    await _get_portfolio(portfolio_id, current_user, db)
    if body.target_value is not None and body.target_value <= 0:
        raise HTTPException(status_code=422, detail="target_value deve ser maior que zero.")
    goal = await update_goal(db, goal_id, portfolio_id, body)
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
    await _get_portfolio(portfolio_id, current_user, db)
    removed = await delete_goal(db, goal_id, portfolio_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Meta nao encontrada.")
