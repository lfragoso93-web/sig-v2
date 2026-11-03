"""Authorized entrypoints for portfolio positions and summary reads."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.services.canonical_positions_service import get_canonical_portfolio_positions
from app.services.portfolio_service import get_portfolio_positions, get_portfolio_summary
from app.services.portfolio_summary_service import get_canonical_portfolio_summary

READ_PORTFOLIO_POSITIONS = "read:portfolio_positions"


async def _authorize(db: AsyncSession, access: PortfolioAccessContext) -> int:
    await get_accessible_portfolio(
        db, access, required_permission=READ_PORTFOLIO_POSITIONS
    )
    if access.user_id is None:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
    return access.user_id


async def get_authorized_legacy_positions(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    user_id = await _authorize(db, access)
    return await get_portfolio_positions(db, access.portfolio_id, user_id)


async def get_authorized_legacy_summary(
    db: AsyncSession, access: PortfolioAccessContext
) -> dict:
    user_id = await _authorize(db, access)
    return await get_portfolio_summary(db, access.portfolio_id, user_id)


async def get_authorized_canonical_positions(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    user_id = await _authorize(db, access)
    return await get_canonical_portfolio_positions(db, access.portfolio_id, user_id)


async def get_authorized_canonical_summary(
    db: AsyncSession, access: PortfolioAccessContext
) -> dict:
    user_id = await _authorize(db, access)
    return await get_canonical_portfolio_summary(db, access.portfolio_id, user_id)
