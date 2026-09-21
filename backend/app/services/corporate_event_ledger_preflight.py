"""Preflight read-only da base de transacoes para eventos corporativos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction


@dataclass(frozen=True)
class LedgerTransactionPreflight:
    portfolio_id: int
    ticker: str
    as_of: date
    transaction_ids: tuple[int, ...]
    first_transaction_date: date | None
    last_transaction_date: date | None
    buy_quantity: Decimal
    sell_quantity: Decimal

    @property
    def net_quantity(self) -> Decimal:
        return self.buy_quantity - self.sell_quantity

    @property
    def transaction_count(self) -> int:
        return len(self.transaction_ids)


async def read_ledger_transaction_preflight(
    db: AsyncSession,
    *,
    portfolio_id: int,
    ticker: str,
    as_of: date,
) -> LedgerTransactionPreflight:
    """Lê transações até ``as_of`` sem alterar a sessão ou o banco."""

    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        raise ValueError("ticker e obrigatorio")

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= as_of,
            func.upper(func.trim(Transaction.ticker)) == clean_ticker,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = tuple(result.scalars().all())
    buy_quantity = sum(
        (
            Decimal(str(transaction.quantity))
            for transaction in transactions
            if transaction.operation == OperationType.buy
        ),
        Decimal("0"),
    )
    sell_quantity = sum(
        (
            Decimal(str(transaction.quantity))
            for transaction in transactions
            if transaction.operation == OperationType.sell
        ),
        Decimal("0"),
    )

    return LedgerTransactionPreflight(
        portfolio_id=portfolio_id,
        ticker=clean_ticker,
        as_of=as_of,
        transaction_ids=tuple(int(transaction.id) for transaction in transactions),
        first_transaction_date=(transactions[0].date if transactions else None),
        last_transaction_date=(transactions[-1].date if transactions else None),
        buy_quantity=buy_quantity,
        sell_quantity=sell_quantity,
    )
