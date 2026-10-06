"""Portfolio ownership lookup governed by an explicit access context."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import (
    AccessPrincipalKind,
    PortfolioAccessContext,
    PortfolioAccessDenied,
)
from app.models.portfolio import Portfolio


async def get_accessible_portfolio(
    db: AsyncSession,
    access: PortfolioAccessContext,
    *,
    required_permission: str,
) -> Portfolio:
    access.require(required_permission)
    query = select(Portfolio).where(Portfolio.id == access.portfolio_id)
    if access.principal_kind is AccessPrincipalKind.USER:
        query = query.where(Portfolio.user_id == access.user_id)

    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
    return portfolio
