from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dividend import Dividend
from app.models.portfolio import Portfolio


async def list_dividends(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[Dividend]:
    # Valida ownership antes de retornar
    portfolio = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not portfolio.scalar_one_or_none():
        raise ValueError("Carteira nao encontrada ou sem permissao")

    result = await db.execute(
        select(Dividend)
        .where(Dividend.portfolio_id == portfolio_id)
        .order_by(Dividend.ex_date.desc())
    )
    return list(result.scalars().all())
