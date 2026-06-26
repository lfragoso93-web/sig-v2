"""
Service de metas financeiras.

Calculos:
  progress_pct  = min(current_value / target_value * 100, 100.0)  [0-100]
  is_completed  = current_value >= target_value
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate


def _enrich(goal: Goal) -> dict:
    progress = 0.0
    if goal.target_value and goal.target_value > 0:
        progress = min(goal.current_value / goal.target_value * 100, 100.0)
    return {
        "id": goal.id,
        "portfolio_id": goal.portfolio_id,
        "name": goal.name,
        "target_value": goal.target_value,
        "current_value": goal.current_value,
        "target_date": goal.target_date,
        "description": goal.description,
        "created_at": goal.created_at,
        "progress_pct": round(progress, 2),
        "is_completed": goal.current_value >= goal.target_value,
    }


async def list_goals(db: AsyncSession, portfolio_id: int) -> list[dict]:
    result = await db.execute(
        select(Goal)
        .where(Goal.portfolio_id == portfolio_id)
        .order_by(Goal.created_at.desc())
    )
    goals = result.scalars().all()
    return [_enrich(g) for g in goals]


async def get_goal(db: AsyncSession, goal_id: int, portfolio_id: int) -> Optional[dict]:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.portfolio_id == portfolio_id)
    )
    goal = result.scalar_one_or_none()
    return _enrich(goal) if goal else None


async def create_goal(db: AsyncSession, data: GoalCreate) -> dict:
    goal = Goal(
        portfolio_id=data.portfolio_id,
        name=data.name,
        target_value=data.target_value,
        current_value=data.current_value,
        target_date=data.target_date,
        description=data.description,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return _enrich(goal)


async def update_goal(db: AsyncSession, goal_id: int, portfolio_id: int, data: GoalUpdate) -> Optional[dict]:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.portfolio_id == portfolio_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    return _enrich(goal)


async def delete_goal(db: AsyncSession, goal_id: int, portfolio_id: int) -> bool:
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.portfolio_id == portfolio_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return False
    await db.delete(goal)
    await db.commit()
    return True
