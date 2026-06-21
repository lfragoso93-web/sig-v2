from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastapi import HTTPException
from app.models.transaction import Transaction, OperationType
from app.models.asset import Asset
from app.schemas.transaction import TransactionCreate


# ---------------------------------------------------------------------------
# Funcoes sincronas auxiliares (usadas pelos testes com mock)
# ---------------------------------------------------------------------------

def _calc_average_price(db: Session, portfolio_id: int, ticker: str) -> float:
    """
    Calcula preco medio ponderado para um ticker em uma carteira.
    Vendas nao alteram o PM — apenas reduzem quantidade e custo proporcional.
    Funciona com db sincrono (Session) para facilitar testes com mock.
    """
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
        .order_by(Transaction.date)
        .all()
    )

    qty = 0.0
    total_cost = 0.0

    for tx in rows:
        op = tx.operation
        is_buy = (
            op == OperationType.buy
            or (hasattr(op, 'value') and op.value == 'buy')
            or str(op).lower() in ('buy', 'compra')
        )
        is_sell = (
            op == OperationType.sell
            or (hasattr(op, 'value') and op.value == 'sell')
            or str(op).lower() in ('sell', 'venda')
        )
        t_qty = float(tx.quantity or 0)
        t_price = float(tx.price or 0)

        if is_buy:
            total_cost += t_qty * t_price
            qty += t_qty
        elif is_sell and qty > 0:
            sell_qty = min(t_qty, qty)
            ratio = sell_qty / qty
            total_cost -= total_cost * ratio
            qty = max(0.0, qty - t_qty)

    if qty <= 0:
        return 0.0
    return total_cost / qty


def _calc_current_quantity(db: Session, portfolio_id: int, ticker: str) -> float:
    """
    Calcula quantidade atual para um ticker em uma carteira.
    Nunca retorna valor negativo.
    Funciona com db sincrono (Session) para facilitar testes com mock.
    """
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
        .all()
    )

    qty = 0.0
    for tx in rows:
        op = tx.operation
        is_buy = (
            op == OperationType.buy
            or (hasattr(op, 'value') and op.value == 'buy')
            or str(op).lower() in ('buy', 'compra')
        )
        is_sell = (
            op == OperationType.sell
            or (hasattr(op, 'value') and op.value == 'sell')
            or str(op).lower() in ('sell', 'venda')
        )
        t_qty = float(tx.quantity or 0)
        if is_buy:
            qty += t_qty
        elif is_sell:
            qty -= t_qty

    return max(0.0, qty)


# ---------------------------------------------------------------------------
# CRUD async
# ---------------------------------------------------------------------------

async def _upsert_asset(db: AsyncSession, ticker: str, asset_type: str) -> None:
    """
    Garante que exista um registro na tabela assets para o ticker.
    Necessario para que quotes_service._db_get_fresh encontre o Asset
    e o cache L1 possa ser populado apos a primeira cotacao via L3.
    Nao sobrescreve last_price nem outros campos ja preenchidos.
    """
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker)
    )
    if result.scalar_one_or_none() is None:
        db.add(Asset(ticker=ticker, asset_type=asset_type))


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
    # Garante registro em assets para habilitar cache L1 de cotacoes
    await _upsert_asset(db, data.ticker, str(data.asset_type))
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
        raise HTTPException(status_code=404, detail="Transacao nao encontrada")
    await db.execute(delete(Transaction).where(Transaction.id == tx_id))
    await db.commit()
