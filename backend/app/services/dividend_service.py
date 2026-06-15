from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.dividend import Dividend
from app.schemas.dividend import DividendCreate
from fastapi import HTTPException


async def create_dividend(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    data: DividendCreate,
) -> Dividend:
    div = Dividend(
        portfolio_id=portfolio_id,
        ticker=data.ticker,
        asset_type=getattr(data, "asset_type", None),
        type=getattr(data, "type", "dividendo"),
        amount=data.amount,
        quantity=getattr(data, "quantity", None),
        payment_date=getattr(data, "payment_date", None),
        date=data.date,
    )
    db.add(div)
    await db.commit()
    await db.refresh(div)
    return div


async def list_dividends(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[Dividend]:
    result = await db.execute(
        select(Dividend)
        .where(Dividend.portfolio_id == portfolio_id)
        .order_by(Dividend.date.desc())
    )
    return list(result.scalars().all())


async def delete_dividend(
    db: AsyncSession,
    dividend_id: int,
    portfolio_id: int,
    user_id: int,
) -> bool:
    result = await db.execute(
        select(Dividend).where(
            Dividend.id == dividend_id,
            Dividend.portfolio_id == portfolio_id,
        )
    )
    div = result.scalar_one_or_none()
    if not div:
        raise HTTPException(status_code=404, detail="Provento não encontrado")
    await db.execute(delete(Dividend).where(Dividend.id == dividend_id))
    await db.commit()
    return True
