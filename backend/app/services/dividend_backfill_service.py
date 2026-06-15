import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.core.asset_types import BR_TYPES

logger = logging.getLogger(__name__)


async def backfill_dividends_from_transactions(
    db: AsyncSession,
    portfolio_id: int,
) -> int:
    """
    Gera registros de Dividend a partir de transacoes do tipo DIVIDENDO/JCP
    que ainda nao possuem entrada correspondente na tabela dividends.
    """
    from app.models.transaction import TransactionType

    result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type.in_([
                TransactionType.DIVIDENDO,
                TransactionType.JCP,
                TransactionType.RENDIMENTO,
            ]),
        )
    )
    transactions = result.scalars().all()

    inserted = 0
    for tx in transactions:
        existing = await db.execute(
            select(Dividend).where(
                Dividend.ticker == tx.ticker,
                Dividend.date == tx.transaction_date,
            )
        )
        if existing.scalar_one_or_none():
            continue

        div = Dividend(
            ticker=tx.ticker,
            date=tx.transaction_date,
            value_per_unit=tx.unit_price,
            total_received=tx.total_cost,
            portfolio_id=portfolio_id,
        )
        db.add(div)
        inserted += 1

    await db.commit()
    logger.info(f"[DividendBackfill] portfolio {portfolio_id}: {inserted} dividendos inseridos")
    return inserted
