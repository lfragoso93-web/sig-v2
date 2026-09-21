"""Preflight read-only da base de transacoes para eventos corporativos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.models.corporate_event import CorporateEvent


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


@dataclass(frozen=True)
class CorporateEventLedgerPreflight:
    event_id: int
    event_type: str
    quantity_factor: Decimal
    ledger: LedgerTransactionPreflight

    @property
    def projected_net_quantity(self) -> Decimal:
        return self.ledger.net_quantity * self.quantity_factor


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


async def read_corporate_event_ledger_preflight(
    db: AsyncSession,
    event: CorporateEvent,
) -> CorporateEventLedgerPreflight:
    """Lê a base do evento e calcula a quantidade projetada sem persistir."""

    if event.portfolio_id is None:
        raise ValueError(
            "preflight do evento exige portfolio_id explicito"
        )

    try:
        quantity_factor = Decimal(str(event.quantity_factor))
    except (InvalidOperation, ValueError):
        raise ValueError("quantity_factor do evento deve ser decimal") from None
    if not quantity_factor.is_finite() or quantity_factor <= 0:
        raise ValueError("quantity_factor do evento deve ser positivo")

    ledger = await read_ledger_transaction_preflight(
        db,
        portfolio_id=int(event.portfolio_id),
        ticker=str(event.ticker),
        as_of=event.effective_date,
    )
    return CorporateEventLedgerPreflight(
        event_id=int(event.id),
        event_type=str(event.event_type),
        quantity_factor=quantity_factor,
        ledger=ledger,
    )
