from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.schemas.asset import AssetCreate
from app.services.asset_service import get_or_create_asset
from app.services.dividend_backfill_service import backfill_dividends
from app.services.asset_onboarding_service import run_onboarding

router = APIRouter()


def _to_operation(value: str) -> OperationType:
    """Converte string 'buy'/'sell' para OperationType com segurança."""
    try:
        return OperationType(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"operation inválida: '{value}'. Use 'buy' ou 'sell'.",
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
        raise HTTPException(status_code=404, detail="Carteira não encontrada.")
    return p


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
                f"Posição atual: {current_qty:.4f} | Tentativa: {quantity:.4f}"
            ),
        )


@router.get("/{portfolio_id}/transactions", response_model=List[TransactionOut])
async def list_transactions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.desc())
    )
    return result.scalars().all()


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

    # Garante que o Asset existe e detecta se e a primeira vez do ticker
    asset_data = AssetCreate(
        ticker=ticker,
        name=ticker,
        asset_type=asset_type,
    )
    _, is_new = await get_or_create_asset(db, asset_data)

    if is_new:
        # Primeira transacao deste ticker: onboarding completo em background
        # (preco historico 5 anos + proventos historicos + logo)
        background_tasks.add_task(run_onboarding, ticker, str(asset_type))
    else:
        # Ativo ja existe: apenas backfill de dividendos desta carteira
        background_tasks.add_task(
            _run_backfill,
            portfolio_id=portfolio_id,
            ticker=ticker,
            asset_type=str(asset_type),
        )

    return tx


@router.patch(
    "/{portfolio_id}/transactions/{transaction_id}",
    response_model=TransactionOut,
)
async def update_transaction(
    portfolio_id: int,
    transaction_id: int,
    payload: TransactionCreate,
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
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
    operation = _to_operation(payload.operation)

    if operation == OperationType.sell:
        await _validate_sell(db, portfolio_id, ticker, payload.quantity, exclude_tx_id=transaction_id)

    tx.ticker = ticker
    tx.asset_type = asset_type
    tx.operation = operation
    tx.quantity = payload.quantity
    tx.price = payload.price
    tx.fees = payload.fees or 0.0
    tx.date = payload.date
    tx.currency = payload.currency or "BRL"
    tx.notes = payload.notes

    await db.commit()
    await db.refresh(tx)

    background_tasks.add_task(
        _run_backfill,
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=str(asset_type),
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
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    ticker = tx.ticker
    asset_type = tx.asset_type

    await db.delete(tx)
    await db.commit()

    background_tasks.add_task(
        _run_backfill,
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=str(asset_type),
    )


async def _run_backfill(portfolio_id: int, ticker: str, asset_type: str) -> None:
    """Abre sessão própria para o background task de backfill de dividendos."""
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await backfill_dividends(
                db=db,
                portfolio_id=portfolio_id,
                ticker=ticker,
                asset_type=asset_type,
            )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).error(
            "[backfill] erro para %s/%s: %s", ticker, portfolio_id, exc
        )
