from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut

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


async def _ensure_migrations(db: AsyncSession) -> None:
    """Migrations inline: garante currency e ticker(100) na tabela transactions."""
    try:
        # currency
        await db.execute(text(
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS "
            "currency VARCHAR(10) NOT NULL DEFAULT 'BRL'"
        ))
        # aumenta ticker para 100 chars (slugs do Tesouro Direto tem ate ~60 chars)
        await db.execute(text(
            "ALTER TABLE transactions ALTER COLUMN ticker TYPE VARCHAR(100)"
        ))
        await db.commit()
    except Exception:
        await db.rollback()


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


@router.post("/{portfolio_id}/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    portfolio_id: int,
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    await _ensure_migrations(db)

    tx = Transaction(
        portfolio_id = portfolio_id,
        ticker       = payload.ticker.upper(),
        asset_type   = payload.asset_type,
        operation    = payload.operation,
        quantity     = payload.quantity,
        price        = payload.price,
        fees         = payload.fees or 0.0,
        date         = payload.date,
        currency     = getattr(payload, 'currency', 'BRL') or 'BRL',
        notes        = payload.notes,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


@router.delete("/{portfolio_id}/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
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

    await db.delete(tx)
    await db.commit()
