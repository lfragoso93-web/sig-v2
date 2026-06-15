import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.core.asset_types import BR_ASSET_TYPES

logger = logging.getLogger(__name__)


async def backfill_dividends(db: AsyncSession, portfolio_id: int) -> int:
    """
    Tenta preencher proventos faltantes consultando yfinance.
    Retorna a quantidade de proventos inseridos.
    """
    try:
        from app.integrations.yfinance_client import get_dividends as yf_dividends
    except ImportError:
        logger.warning("yfinance não disponível para backfill")
        return 0

    result = await db.execute(
        select(Transaction.ticker).distinct()
        .where(Transaction.portfolio_id == portfolio_id)
    )
    tickers = [row[0] for row in result.fetchall()]

    inserted = 0
    for ticker in tickers:
        try:
            dividends = yf_dividends(ticker)
            for dt, amount in dividends.items():
                exists = await db.execute(
                    select(Dividend).where(
                        Dividend.portfolio_id == portfolio_id,
                        Dividend.ticker == ticker,
                        Dividend.date == dt.date(),
                    )
                )
                if exists.scalar_one_or_none():
                    continue
                div = Dividend(
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    amount=float(amount),
                    date=dt.date(),
                    source="yfinance_backfill",
                )
                db.add(div)
                inserted += 1
        except Exception as exc:
            logger.warning(f"Erro backfill {ticker}: {exc}")

    if inserted:
        await db.commit()
    return inserted


def is_br_type(asset_type: str) -> bool:
    return asset_type in BR_ASSET_TYPES
