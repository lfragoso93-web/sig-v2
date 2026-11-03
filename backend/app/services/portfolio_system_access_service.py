"""Explicit system authorization for narrowly scoped portfolio operations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.repositories.portfolio_access_repository import get_accessible_portfolio


async def authorize_system_portfolio_operation(
    db: AsyncSession,
    portfolio_id: int,
    *,
    permission: str,
    purpose: str,
) -> PortfolioAccessContext:
    """Validate a system principal against an existing portfolio before access."""
    access = PortfolioAccessContext.for_system(
        portfolio_id=portfolio_id,
        permissions=frozenset({permission}),
        purpose=purpose,
    )
    await get_accessible_portfolio(db, access, required_permission=permission)
    return access
