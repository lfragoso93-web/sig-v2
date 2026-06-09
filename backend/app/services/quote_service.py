import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.position import Position
from app.integrations.brapi import fetch_quotes
from app.integrations.yfinance_client import fetch_international_quotes, INTERNATIONAL_TYPES

logger = logging.getLogger(__name__)

NATIONAL_TYPES = {
    "acao nacional",
    "fii",
    "etf nacional",
    "tesouro direto",
}


async def update_quotes_for_portfolio(portfolio_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()

    national      = [p for p in positions if p.asset_type.lower() in NATIONAL_TYPES]
    international = [p for p in positions if p.asset_type.lower() in INTERNATIONAL_TYPES]

    quotes: dict[str, float] = {}

    # BRAPI — ativos nacionais
    if national:
        nat_quotes = await fetch_quotes([p.ticker for p in national])
        quotes.update(nat_quotes)

    # yfinance — stocks, ETFs internacionais, criptos
    if international:
        intl_quotes = await fetch_international_quotes(
            tickers=[p.ticker for p in international],
            asset_types={p.ticker: p.asset_type for p in international},
        )
        quotes.update(intl_quotes)

    updated = 0
    for pos in positions:
        price = quotes.get(pos.ticker)
        if price is not None:
            pos.current_price = price
            pos.current_value = price * pos.quantity
            updated += 1

    await db.commit()
    logger.info(f"Portfolio {portfolio_id}: {updated}/{len(positions)} posicoes atualizadas")
    return updated


async def update_all_quotes(db: AsyncSession) -> None:
    result = await db.execute(select(Position))
    all_positions = result.scalars().all()

    national      = [p for p in all_positions if p.asset_type.lower() in NATIONAL_TYPES]
    international = [p for p in all_positions if p.asset_type.lower() in INTERNATIONAL_TYPES]

    quotes: dict[str, float] = {}

    if national:
        tickers = list({p.ticker for p in national})
        quotes.update(await fetch_quotes(tickers))

    if international:
        tickers  = list({p.ticker for p in international})
        at_map   = {p.ticker: p.asset_type for p in international}
        quotes.update(await fetch_international_quotes(tickers, at_map))

    updated = 0
    for pos in all_positions:
        price = quotes.get(pos.ticker)
        if price is not None:
            pos.current_price = price
            pos.current_value = price * pos.quantity
            updated += 1

    await db.commit()
    logger.info(f"[scheduler] {updated} posicoes atualizadas")
