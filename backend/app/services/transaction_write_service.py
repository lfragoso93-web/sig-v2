"""Canonical transaction write service shared by HTTP, CSV and certification callers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.transaction import OperationType, Transaction
from app.schemas.transaction import TransactionCreate
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_financially_certified_crypto_asset,
)
from app.services.treasury_catalog_service import resolve_treasury_symbol


class TransactionWriteError(ValueError):
    """Raised when a transaction violates canonical write rules."""


async def _current_quantity(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
) -> float:
    result = await db.execute(
        select(Transaction.operation, Transaction.quantity).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
            Transaction.asset_type == asset_type,
        )
    )
    quantity = 0.0
    for operation, value in result.all():
        op = operation.value if isinstance(operation, OperationType) else str(operation)
        if op == OperationType.buy.value:
            quantity += float(value)
        elif op == OperationType.sell.value:
            quantity -= float(value)
    return max(quantity, 0.0)


async def _add_catalog_asset_if_missing(
    db: AsyncSession,
    *,
    ticker: str,
    asset_type: str,
    currency: str,
    flush: bool,
) -> None:
    result = await db.execute(
        select(Asset).where(
            Asset.ticker.ilike(ticker),
            Asset.asset_type == asset_type,
        )
    )
    if result.scalar_one_or_none() is not None:
        return

    db.add(
        Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type,
            currency=currency,
        )
    )
    if flush:
        await db.flush()


async def add_transaction_record(
    db: AsyncSession,
    *,
    portfolio_id: int,
    payload: TransactionCreate,
    flush: bool = False,
) -> Transaction:
    """Add one transaction using the canonical domain write path.

    This function deliberately does not commit, refresh, or schedule snapshots/cache
    invalidation; callers own transaction boundaries and post-commit orchestration.
    """
    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
    if asset_type == "TESOURO_DIRETO":
        canonical_ticker = await resolve_treasury_symbol(db, payload.ticker)
        if canonical_ticker:
            ticker = canonical_ticker.strip().upper()
    try:
        operation = OperationType(payload.operation)
    except ValueError as exc:
        raise TransactionWriteError(
            f"operation invalida: '{payload.operation}'. Use 'buy' ou 'sell'."
        ) from exc

    if asset_type == "CRIPTO":
        try:
            await require_financially_certified_crypto_asset(db, ticker)
        except CryptoTransactionEligibilityError as exc:
            raise TransactionWriteError(str(exc)) from exc

    if operation == OperationType.sell:
        current_qty = await _current_quantity(db, portfolio_id, ticker, asset_type)
        if payload.quantity > current_qty:
            raise TransactionWriteError(
                f"Quantidade insuficiente para venda de {ticker}. "
                f"Posicao atual: {current_qty:.4f} | Tentativa: {payload.quantity:.4f}"
            )

    currency = payload.currency or "BRL"
    if asset_type != "CRIPTO":
        await _add_catalog_asset_if_missing(
            db,
            ticker=ticker,
            asset_type=asset_type,
            currency=currency,
            flush=flush,
        )

    transaction = Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=asset_type,
        operation=operation,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees or 0.0,
        date=payload.date,
        currency=currency,
        notes=payload.notes,
    )
    db.add(transaction)

    if flush:
        await db.flush()

    return transaction


async def create_transaction_record(
    db: AsyncSession,
    *,
    portfolio_id: int,
    payload: TransactionCreate,
) -> Transaction:
    """Persist one transaction using the canonical domain write path.

    This function deliberately does not schedule snapshots/cache invalidation;
    callers own post-commit orchestration appropriate to their surface.
    """
    transaction = await add_transaction_record(
        db,
        portfolio_id=portfolio_id,
        payload=payload,
    )
    await db.commit()
    await db.refresh(transaction)
    return transaction
