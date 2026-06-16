import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models.dividend import Dividend
from app.models.portfolio import Portfolio
from app.schemas.dividend import DividendCreate

logger = logging.getLogger(__name__)


async def create_dividend(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    data: DividendCreate,
) -> Dividend:
    # Valida ownership da carteira
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise ValueError("Carteira nao encontrada ou sem permissao")

    existing = await db.execute(
        select(Dividend).where(
            Dividend.ticker == data.ticker,
            Dividend.ex_date == data.ex_date,
            Dividend.portfolio_id == portfolio_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Dividendo ja existe para este ticker e data ex")

    div = Dividend(
        ticker=data.ticker,
        ex_date=data.ex_date,
        payment_date=data.payment_date,
        value_per_unit=data.value_per_unit,
        dividend_type=data.dividend_type,
        portfolio_id=portfolio_id,
    )
    db.add(div)
    await db.commit()
    await db.refresh(div)
    logger.info(f"[DividendService] Criado dividendo {div.ticker} ex={div.ex_date}")
    return div


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


async def delete_dividend(
    db: AsyncSession,
    dividend_id: int,
    portfolio_id: int,
    user_id: int,
) -> bool:
    # Valida ownership da carteira
    portfolio = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not portfolio.scalar_one_or_none():
        return False

    result = await db.execute(
        select(Dividend).where(
            Dividend.id == dividend_id,
            Dividend.portfolio_id == portfolio_id,
        )
    )
    div = result.scalar_one_or_none()
    if not div:
        return False

    await db.delete(div)
    await db.commit()
    logger.info(f"[DividendService] Deletado dividendo id={dividend_id}")
    return True
