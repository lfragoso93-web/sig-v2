"""Authorized entrypoints for portfolio goals and class allocation targets."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.class_target_service import (
    bulk_upsert_targets,
    delete_target,
    get_targets,
    get_targets_with_current,
    upsert_target,
)
from app.services.goals_service import (
    create_goal,
    delete_goal,
    get_goal,
    list_goals,
    update_goal,
)
from app.services.portfolio_service import get_asset_distribution

READ_PORTFOLIO_GOALS = "read:portfolio_goals"
WRITE_PORTFOLIO_GOALS = "write:portfolio_goals"
READ_PORTFOLIO_CLASS_TARGETS = "read:portfolio_class_targets"
WRITE_PORTFOLIO_CLASS_TARGETS = "write:portfolio_class_targets"


async def _authorize(
    db: AsyncSession, access: PortfolioAccessContext, permission: str
) -> int:
    await get_accessible_portfolio(db, access, required_permission=permission)
    if access.user_id is None:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
    return access.user_id


async def get_authorized_goals(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    user_id = await _authorize(db, access, READ_PORTFOLIO_GOALS)
    return await list_goals(db, access.portfolio_id, user_id)


async def get_authorized_goal(
    db: AsyncSession, access: PortfolioAccessContext, goal_id: int
) -> dict | None:
    user_id = await _authorize(db, access, READ_PORTFOLIO_GOALS)
    return await get_goal(db, goal_id, access.portfolio_id, user_id)


async def create_authorized_goal(
    db: AsyncSession, access: PortfolioAccessContext, data: GoalCreate
) -> dict:
    user_id = await _authorize(db, access, WRITE_PORTFOLIO_GOALS)
    data.portfolio_id = access.portfolio_id
    return await create_goal(db, data, user_id)


async def update_authorized_goal(
    db: AsyncSession,
    access: PortfolioAccessContext,
    goal_id: int,
    data: GoalUpdate,
) -> dict | None:
    user_id = await _authorize(db, access, WRITE_PORTFOLIO_GOALS)
    return await update_goal(db, goal_id, access.portfolio_id, data, user_id)


async def delete_authorized_goal(
    db: AsyncSession, access: PortfolioAccessContext, goal_id: int
) -> bool:
    await _authorize(db, access, WRITE_PORTFOLIO_GOALS)
    return await delete_goal(db, goal_id, access.portfolio_id)


async def get_authorized_class_targets(
    db: AsyncSession, access: PortfolioAccessContext
):
    await _authorize(db, access, READ_PORTFOLIO_CLASS_TARGETS)
    return await get_targets(db, access.portfolio_id)


async def get_authorized_class_targets_with_current(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    user_id = await _authorize(db, access, READ_PORTFOLIO_CLASS_TARGETS)
    distribution = await get_asset_distribution(db, access.portfolio_id, user_id)
    return await get_targets_with_current(db, access.portfolio_id, distribution)


async def set_authorized_class_targets(
    db: AsyncSession,
    access: PortfolioAccessContext,
    items: list[tuple[str, float]],
):
    await _authorize(db, access, WRITE_PORTFOLIO_CLASS_TARGETS)
    return await bulk_upsert_targets(db, access.portfolio_id, items)


async def set_authorized_class_target(
    db: AsyncSession, access: PortfolioAccessContext, asset_type: str, target_pct: float
):
    await _authorize(db, access, WRITE_PORTFOLIO_CLASS_TARGETS)
    return await upsert_target(db, access.portfolio_id, asset_type, target_pct)


async def delete_authorized_class_target(
    db: AsyncSession, access: PortfolioAccessContext, asset_type: str
) -> bool:
    await _authorize(db, access, WRITE_PORTFOLIO_CLASS_TARGETS)
    return await delete_target(db, access.portfolio_id, asset_type)
