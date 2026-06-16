import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dividend import Dividend
from app.schemas.dividend import DividendCreate

logger = logging.getLogger(__name__)


async def create_dividend(
    db: AsyncSession,
    data: DividendCreate,
    portfolio_id: int,
) -> Dividend:
    existing = await db.execute(
        select(Dividend).where(
            Dividend.ticker == data.ticker,
            Dividend.ex_date == data.ex_date,
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
) -> list[Dividend]:
    result = await db.execute(
        select(Dividend).where(Dividend.portfolio_id == portfolio_id)
    )
    return list(result.scalars().all())
