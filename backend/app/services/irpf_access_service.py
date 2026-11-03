"""Authorized entry points for portfolio-scoped IRPF calculations."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.services.irpf_bens_direitos_service import calc_bens_direitos
from app.services.irpf_tax_service import calc_ganhos_capital, calc_rendimentos

READ_PORTFOLIO_IRPF = "read:portfolio_irpf"


async def require_irpf_access(db: AsyncSession, access: PortfolioAccessContext) -> None:
    await get_accessible_portfolio(
        db, access, required_permission=READ_PORTFOLIO_IRPF
    )


async def read_irpf_assets(db: AsyncSession, access: PortfolioAccessContext, year: int):
    await require_irpf_access(db, access)
    return await calc_bens_direitos(db, access.portfolio_id, year)


async def read_irpf_capital_gains(
    db: AsyncSession, access: PortfolioAccessContext, year: int
):
    await require_irpf_access(db, access)
    return await calc_ganhos_capital(db, access.portfolio_id, year)


async def read_irpf_income(db: AsyncSession, access: PortfolioAccessContext, year: int):
    await require_irpf_access(db, access)
    return await calc_rendimentos(db, access.portfolio_id, year)
