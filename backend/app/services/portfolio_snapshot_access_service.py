"""System authorization for portfolio snapshot maintenance and rebuilds."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.repositories.portfolio_access_repository import get_accessible_portfolio

MAINTAIN_PORTFOLIO_SNAPSHOTS = "maintain:portfolio_snapshots"


async def authorize_system_snapshot_maintenance(
    db: AsyncSession,
    portfolio_id: int,
    *,
    purpose: str,
) -> PortfolioAccessContext:
    access = PortfolioAccessContext.for_system(
        portfolio_id=portfolio_id,
        permissions=frozenset({MAINTAIN_PORTFOLIO_SNAPSHOTS}),
        purpose=purpose,
    )
    await get_accessible_portfolio(
        db,
        access,
        required_permission=MAINTAIN_PORTFOLIO_SNAPSHOTS,
    )
    return access
