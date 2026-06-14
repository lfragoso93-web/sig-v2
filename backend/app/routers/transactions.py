from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate
from app.services.dividend_backfill_service import backfill_dividends

router = APIRouter()


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

    ticker     = payload.ticker.upper()
    asset_type = payload.asset_type

    tx = Transaction(
        portfolio_id = portfolio_id,
        ticker       = ticker,
        asset_type   = asset_type,
        operation    = payload.operation,
        quantity     = payload.quantity,
        price        = payload.price,
        fees         = payload.fees or 0.0,
        date         = payload.date,
        currency     = getattr(payload, "currency", "BRL") or "BRL",
        notes        = payload.notes,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    # ─ Backfill de proventos em background — transparente ao usuário
    # Uma nova sessão é criada dentro do backfill para não reusar a sessão
    # já fechada pelo commit acima.
    background_tasks.add_task(
        _run_backfill,
        portfolio_id = portfolio_id,
        ticker       = ticker,
        asset_type   = str(asset_type),
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
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    data = payload.model_dump(exclude_unset=True)

    # Se alterar o ticker ou asset_type, usamos os novos valores no backfill
    ticker     = data.get("ticker", tx.ticker).upper()
    asset_type = data.get("asset_type", tx.asset_type)

    for field, value in data.items():
        if field == "ticker" and value is not None:
            setattr(tx, field, value.upper())
        elif value is not None:
            setattr(tx, field, value)

    await db.commit()
    await db.refresh(tx)

    background_tasks.add_task(
        _run_backfill,
        portfolio_id = portfolio_id,
        ticker       = ticker,
        asset_type   = str(asset_type),
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

    ticker     = tx.ticker
    asset_type = tx.asset_type

    await db.delete(tx)
    await db.commit()

    # Reprocessa proventos após exclusão — recalcula quantidades na data-ex
    background_tasks.add_task(
        _run_backfill,
        portfolio_id = portfolio_id,
        ticker       = ticker,
        asset_type   = str(asset_type),
    )


async def _run_backfill(portfolio_id: int, ticker: str, asset_type: str) -> None:
    """
    Wrapper que abre uma sessão independente para o backfill.
    BackgroundTasks do FastAPI não recebem Depends, então gerenciamos
    o ciclo de vida da sessão manualmente aqui.
    """
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await backfill_dividends(
            db          = db,
            portfolio_id = portfolio_id,
            ticker       = ticker,
            asset_type   = asset_type,
        )
