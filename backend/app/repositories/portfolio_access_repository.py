"""Portfolio ownership lookup governed by an explicit access context."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import (
    AccessPrincipalKind,
    PortfolioAccessContext,
    PortfolioAccessDenied,
)
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction


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
    elif access.principal_kind is not AccessPrincipalKind.SYSTEM:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")

    result = await db.execute(query)
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
    return portfolio


async def get_accessible_transaction(
    db: AsyncSession,
    access: PortfolioAccessContext,
    *,
    transaction_id: int,
    required_permission: str,
) -> Transaction:
    """Load a transaction only when both its portfolio and caller are in scope."""
    access.require(required_permission)
    query = (
        select(Transaction)
        .join(Portfolio, Portfolio.id == Transaction.portfolio_id)
        .where(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == access.portfolio_id,
        )
    )
    if access.principal_kind is AccessPrincipalKind.USER:
        query = query.where(Portfolio.user_id == access.user_id)
    elif access.principal_kind is not AccessPrincipalKind.SYSTEM:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")

    result = await db.execute(query)
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
    return transaction
