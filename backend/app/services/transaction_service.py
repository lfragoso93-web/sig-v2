from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate


async def create_transaction(
    db: AsyncSession,
    portfolio_id: int,
    data: TransactionCreate,
) -> Transaction:
    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=data.ticker,
        asset_type=data.asset_type,
        operation=data.operation,
        quantity=data.quantity,
        price=data.price,
        fees=getattr(data, "fees", 0.0),
        date=data.date,
        currency=getattr(data, "currency", "BRL"),
        notes=getattr(data, "notes", None),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def list_transactions(db: AsyncSession, portfolio_id: int) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.desc())
    )
    return list(result.scalars().all())


async def delete_transaction(db: AsyncSession, tx_id: int, portfolio_id: int) -> None:
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == tx_id,
            Transaction.portfolio_id == portfolio_id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    await db.execute(delete(Transaction).where(Transaction.id == tx_id))
    await db.commit()
