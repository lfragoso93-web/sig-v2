"""Preflight read-only da base de transacoes para eventos corporativos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

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


@dataclass(frozen=True)
class CorporateEventLedgerPreflightReport:
    schema_version: str
    dry_run: bool
    database_writes_executed: int
    ready_for_execution: bool
    preflight: CorporateEventLedgerPreflight

    def to_dict(self) -> dict[str, Any]:
        ledger = self.preflight.ledger
        return {
            "schema_version": self.schema_version,
            "dry_run": self.dry_run,
            "database_writes_executed": self.database_writes_executed,
            "ready_for_execution": self.ready_for_execution,
            "event_id": self.preflight.event_id,
            "event_type": self.preflight.event_type,
            "quantity_factor": str(self.preflight.quantity_factor),
            "portfolio_id": ledger.portfolio_id,
            "ticker": ledger.ticker,
            "as_of": ledger.as_of.isoformat(),
            "transaction_ids": list(ledger.transaction_ids),
            "transaction_count": ledger.transaction_count,
            "first_transaction_date": (
                ledger.first_transaction_date.isoformat()
                if ledger.first_transaction_date is not None
                else None
            ),
            "last_transaction_date": (
                ledger.last_transaction_date.isoformat()
                if ledger.last_transaction_date is not None
                else None
            ),
            "buy_quantity": str(ledger.buy_quantity),
            "sell_quantity": str(ledger.sell_quantity),
            "net_quantity": str(ledger.net_quantity),
            "projected_net_quantity": str(
                self.preflight.projected_net_quantity
            ),
        }


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
    *,
    portfolio_id: int | None = None,
) -> CorporateEventLedgerPreflight:
    """Lê a base do evento e calcula a quantidade projetada sem persistir."""

    effective_portfolio_id = (
        portfolio_id if portfolio_id is not None else event.portfolio_id
    )
    if effective_portfolio_id is None:
        raise ValueError(
            "preflight do evento exige portfolio_id explicito"
        )
    if effective_portfolio_id <= 0:
        raise ValueError("portfolio_id explicito deve ser positivo")

    try:
        quantity_factor = Decimal(str(event.quantity_factor))
    except (InvalidOperation, ValueError):
        raise ValueError("quantity_factor do evento deve ser decimal") from None
    if not quantity_factor.is_finite() or quantity_factor <= 0:
        raise ValueError("quantity_factor do evento deve ser positivo")

    ledger = await read_ledger_transaction_preflight(
        db,
        portfolio_id=int(effective_portfolio_id),
        ticker=str(event.ticker),
        as_of=event.effective_date,
    )
    return CorporateEventLedgerPreflight(
        event_id=int(event.id),
        event_type=str(event.event_type),
        quantity_factor=quantity_factor,
        ledger=ledger,
    )


async def build_corporate_event_ledger_preflight_report(
    db: AsyncSession,
    event: CorporateEvent,
    *,
    portfolio_id: int | None = None,
) -> CorporateEventLedgerPreflightReport:
    preflight = await read_corporate_event_ledger_preflight(
        db,
        event,
        portfolio_id=portfolio_id,
    )
    return CorporateEventLedgerPreflightReport(
        schema_version="corporate-event-ledger-preflight.v1",
        dry_run=True,
        database_writes_executed=0,
        ready_for_execution=False,
        preflight=preflight,
    )
