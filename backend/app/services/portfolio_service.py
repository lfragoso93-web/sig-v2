from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.portfolio import Portfolio
from app.models.system_config import SystemConfig
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from typing import Optional


async def _get_max_portfolios(db: AsyncSession) -> int:
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "max_portfolios_per_user")
    )
    config = result.scalar_one_or_none()
    return int(config.value) if config else 10


async def get_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira não encontrada")
    return portfolio


async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at.desc())
    )
    return result.scalars().all()


async def create_portfolio(
    db: AsyncSession, user_id: int, data: PortfolioCreate
) -> Portfolio:
    # Verifica limite de carteiras
    count_result = await db.execute(
        select(func.count()).select_from(Portfolio).where(Portfolio.user_id == user_id)
    )
    count = count_result.scalar_one()
    max_portfolios = await _get_max_portfolios(db)
    if count >= max_portfolios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {max_portfolios} carteiras atingido",
        )
    portfolio = Portfolio(user_id=user_id, name=data.name, description=data.description)
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def update_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int, data: PortfolioUpdate
) -> Portfolio:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    if data.name is not None:
        portfolio.name = data.name
    if data.description is not None:
        portfolio.description = data.description
    if data.is_active is not None:
        portfolio.is_active = data.is_active
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def delete_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> None:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    await db.delete(portfolio)
