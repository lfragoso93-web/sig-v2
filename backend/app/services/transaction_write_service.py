"""Canonical transaction write service shared by HTTP and certification callers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.schemas.asset import AssetCreate
from app.schemas.transaction import TransactionCreate
from app.services.asset_service import get_or_create_asset
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_financially_certified_crypto_asset,
)


class TransactionWriteError(ValueError):
    """Raised when a transaction violates canonical write rules."""


async def _current_quantity(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
) -> float:
    result = await db.execute(
        select(Transaction.operation, Transaction.quantity).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
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
    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
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
        current_qty = await _current_quantity(db, portfolio_id, ticker)
        if payload.quantity > current_qty:
            raise TransactionWriteError(
                f"Quantidade insuficiente para venda de {ticker}. "
                f"Posicao atual: {current_qty:.4f} | Tentativa: {payload.quantity:.4f}"
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
        currency=payload.currency or "BRL",
        notes=payload.notes,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    if asset_type != "CRIPTO":
        await get_or_create_asset(
            db,
            AssetCreate(ticker=ticker, name=ticker, asset_type=asset_type),
        )

    return transaction
