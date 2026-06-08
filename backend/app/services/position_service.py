from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.portfolio_position import PortfolioPosition
from app.models.portfolio import Portfolio
from app.schemas.position import PositionResponse, PortfolioSummary
from app.core.cache import cache_get
from decimal import Decimal
from typing import Optional


async def get_positions(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[PortfolioPosition]:
    # Garante que a carteira pertence ao usuário
    portfolio_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not portfolio_result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Carteira não encontrada")

    result = await db.execute(
        select(PortfolioPosition)
        .options(selectinload(PortfolioPosition.asset))
        .where(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.quantity > 0,
        )
        .order_by(PortfolioPosition.asset_id)
    )
    return result.scalars().all()


async def enrich_with_current_prices(
    positions: list[PortfolioPosition],
) -> list[dict]:
    """
    Adiciona preço atual, valor atual e lucro não-realizado a cada posição.
    Busca preços no cache Redis (alimentado pelo scheduler/BRAPI).
    """
    enriched = []
    for pos in positions:
        data = {
            "id": pos.id,
            "portfolio_id": pos.portfolio_id,
            "asset_id": pos.asset_id,
            "asset": pos.asset,
            "quantity": pos.quantity,
            "average_price": pos.average_price,
            "total_invested": pos.total_invested,
            "realized_profit": pos.realized_profit,
            "current_price": None,
            "current_value": None,
            "unrealized_profit": None,
            "unrealized_profit_pct": None,
            "updated_at": pos.updated_at,
        }
        # Tenta buscar preço no cache Redis
        cache_key = f"quote:{pos.asset.brapi_ticker or pos.asset.ticker}"
        cached = await cache_get(cache_key)
        if cached and "regularMarketPrice" in cached:
            current_price = Decimal(str(cached["regularMarketPrice"]))
            current_value = (pos.quantity * current_price).quantize(Decimal("0.01"))
            unrealized = current_value - pos.total_invested
            pct = (
                (unrealized / pos.total_invested * 100).quantize(Decimal("0.01"))
                if pos.total_invested > 0
                else Decimal("0")
            )
            data["current_price"] = current_price
            data["current_value"] = current_value
            data["unrealized_profit"] = unrealized
            data["unrealized_profit_pct"] = pct
        enriched.append(data)
    return enriched


async def get_portfolio_summary(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> PortfolioSummary:
    portfolio_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Carteira não encontrada")

    positions = await get_positions(db, portfolio_id, user_id)
    enriched = await enrich_with_current_prices(positions)

    total_invested = sum(p["total_invested"] for p in enriched)
    current_value = sum(
        p["current_value"] for p in enriched if p["current_value"] is not None
    ) or None
    realized_profit = sum(p["realized_profit"] for p in enriched)
    total_return = (current_value - total_invested) if current_value else None
    total_return_pct = (
        (total_return / total_invested * 100).quantize(Decimal("0.01"))
        if total_return is not None and total_invested > 0
        else None
    )

    return PortfolioSummary(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio.name,
        total_invested=total_invested,
        current_value=current_value,
        total_return=total_return,
        total_return_pct=total_return_pct,
        realized_profit=realized_profit,
        positions_count=len(enriched),
        positions=enriched,
    )
