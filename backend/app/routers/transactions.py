import logging
from datetime import date as DateType
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.models.user import User
from app.schemas.asset import AssetCreate
from app.schemas.transaction import (
    PagedTransactions,
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from app.services.asset_service import get_or_create_asset
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_financially_certified_crypto_asset,
)
from app.services.portfolio_service import invalidate_portfolio_cache
from app.services.transaction_service import list_transactions_paginated

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_operation(value: str) -> OperationType:
    try:
        return OperationType(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"operation invalida: '{value}'. Use 'buy' ou 'sell'.",
        )


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return p


async def _validate_crypto_transaction_asset(
    db: AsyncSession,
    ticker: str,
    asset_type: str,
) -> None:
    if asset_type != "CRIPTO":
        return

    try:
        await require_financially_certified_crypto_asset(db, ticker)
    except CryptoTransactionEligibilityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _calc_current_quantity(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    exclude_tx_id: int | None = None,
) -> float:
    stmt = select(Transaction.operation, Transaction.quantity).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.ticker == ticker,
    )
    if exclude_tx_id is not None:
        stmt = stmt.where(Transaction.id != exclude_tx_id)

    result = await db.execute(stmt)
    rows = result.all()

    qty = 0.0
    for op, q in rows:
        op_val = op.value if isinstance(op, OperationType) else str(op)
        if op_val == "buy":
            qty += float(q)
        elif op_val == "sell":
            qty -= float(q)
    return max(qty, 0.0)


async def _validate_sell(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    quantity: float,
    exclude_tx_id: int | None = None,
) -> None:
    current_qty = await _calc_current_quantity(db, portfolio_id, ticker, exclude_tx_id)
    if quantity > current_qty:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Quantidade insuficiente para venda de {ticker}. "
                f"Posicao atual: {current_qty:.4f} | Tentativa: {quantity:.4f}"
            ),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{portfolio_id}/transactions", response_model=PagedTransactions)
async def list_transactions(
    portfolio_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ticker: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    date_from: Optional[DateType] = Query(None),
    date_to: Optional[DateType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    if operation and operation.lower() not in {"buy", "sell"}:
        raise HTTPException(
            status_code=422,
            detail=f"operation invalida: '{operation}'. Use 'buy' ou 'sell'.",
        )

    return await list_transactions_paginated(
        db=db,
        portfolio_id=portfolio_id,
        page=page,
        page_size=page_size,
        ticker=ticker,
        operation=operation,
        date_from=date_from,
        date_to=date_to,
    )


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    portfolio_id: int,
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
    operation = _to_operation(payload.operation)

    await _validate_crypto_transaction_asset(db, ticker, asset_type)

    if operation == OperationType.sell:
        await _validate_sell(db, portfolio_id, ticker, payload.quantity)

    tx = Transaction(
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
    db.add(tx)


    await db.commit()
    await db.refresh(tx)

    if asset_type != "CRIPTO":
        asset_data = AssetCreate(ticker=ticker, name=ticker, asset_type=asset_type)
        await get_or_create_asset(db, asset_data)

    # O CRUD de transacoes deve permanecer deterministico e local. Ingestao de
    # mercado (precos, logos, eventos e proventos) pertence a pipelines opt-in.
    background_tasks.add_task(
        _run_snapshot_backfill,
        portfolio_id=portfolio_id,
        tx_date=payload.date,
    )
    background_tasks.add_task(
        invalidate_portfolio_cache,
        portfolio_id=portfolio_id,
    )

    return tx


@router.patch(
    "/{portfolio_id}/transactions/{transaction_id}",
    response_model=TransactionOut,
)
async def update_transaction(
    portfolio_id: int,
    transaction_id: int,
    payload: TransactionUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada.")

    ticker = payload.ticker.strip().upper() if payload.ticker is not None else tx.ticker
    asset_type = payload.asset_type if payload.asset_type is not None else tx.asset_type
    operation = (
        _to_operation(payload.operation)
        if payload.operation is not None
        else tx.operation
    )
    quantity = payload.quantity if payload.quantity is not None else tx.quantity
    price = payload.price if payload.price is not None else tx.price
    fees = payload.fees if payload.fees is not None else tx.fees
    tx_date = payload.date if payload.date is not None else tx.date
    currency = payload.currency if payload.currency is not None else tx.currency
    notes = payload.notes if "notes" in payload.model_fields_set else tx.notes

    await _validate_crypto_transaction_asset(db, ticker, asset_type)

    if operation == OperationType.sell:
        await _validate_sell(
            db,
            portfolio_id,
            ticker,
            quantity,
            exclude_tx_id=transaction_id,
        )

    invalidate_from = min(tx.date, tx_date)

    tx.ticker = ticker
    tx.asset_type = asset_type
    tx.operation = operation
    tx.quantity = quantity
    tx.price = price
    tx.fees = fees
    tx.date = tx_date
    tx.currency = currency
    tx.notes = notes


    await db.commit()
    await db.refresh(tx)

    background_tasks.add_task(
        _run_snapshot_backfill,
        portfolio_id=portfolio_id,
        tx_date=invalidate_from,
    )
    background_tasks.add_task(
        invalidate_portfolio_cache,
        portfolio_id=portfolio_id,
    )

    return tx


@router.delete(
    "/{portfolio_id}/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada.")

    tx_date = tx.date

    await db.delete(tx)
    await db.commit()

    background_tasks.add_task(
        _run_snapshot_backfill,
        portfolio_id=portfolio_id,
        tx_date=tx_date,
    )
    background_tasks.add_task(
        invalidate_portfolio_cache,
        portfolio_id=portfolio_id,
    )


# ---------------------------------------------------------------------------
# Background tasks locais
# ---------------------------------------------------------------------------


async def _run_snapshot_backfill(portfolio_id: int, tx_date: DateType) -> None:
    try:
        from app.services.portfolio_snapshot_service import (
            backfill_snapshots,
            invalidate_snapshots_from,
        )

        async with AsyncSessionLocal() as db:
            deleted = await invalidate_snapshots_from(db, portfolio_id, tx_date)
            log.info(
                (
                    "[snapshot_backfill] portfolio=%s invalida a partir de %s "
                    "(%s removidos)"
                ),
                portfolio_id,
                tx_date,
                deleted,
            )
            count = await backfill_snapshots(db=db, portfolio_id=portfolio_id)
            log.info(
                "[snapshot_backfill] portfolio=%s — %s snapshots recalculados",
                portfolio_id,
                count,
            )
    except Exception as exc:
        log.error("[snapshot_backfill] erro para portfolio %s: %s", portfolio_id, exc)
