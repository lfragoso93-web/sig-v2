from sqlalchemy.orm import Session
from sqlalchemy import and_, extract
from datetime import date
from app.models.transaction import Transaction, OperationType
from app.models.portfolio import Portfolio
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionOut
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _calc_average_price(db: Session, portfolio_id: int, ticker: str) -> float:
    """Preco medio ponderado em BRL para um ticker dentro de uma carteira."""
    rows = (
        db.query(
            Transaction.operation,
            Transaction.quantity,
            Transaction.price,
        )
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
        .order_by(Transaction.date.asc())
        .all()
    )

    qty = 0.0
    cost = 0.0
    for r in rows:
        unit_price = float(r.price)
        if r.operation == OperationType.buy:
            qty += float(r.quantity)
            cost += float(r.quantity) * unit_price
        elif r.operation == OperationType.sell:
            sold = min(float(r.quantity), qty)
            if qty > 0:
                avg = cost / qty
                cost -= sold * avg
            qty -= sold
            qty = max(qty, 0.0)
            cost = max(cost, 0.0)

    return round(cost / qty, 6) if qty > 0 else 0.0


def _calc_current_quantity(db: Session, portfolio_id: int, ticker: str) -> float:
    """Retorna a quantidade atual em carteira para um ticker."""
    rows = (
        db.query(Transaction.operation, Transaction.quantity)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
        .all()
    )
    qty = 0.0
    for r in rows:
        if r.operation == OperationType.buy:
            qty += float(r.quantity)
        elif r.operation == OperationType.sell:
            qty -= float(r.quantity)
    return max(qty, 0.0)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_transaction(
    db: Session,
    portfolio_id: int,
    user_id: int,
    data: TransactionCreate,
) -> TransactionOut:
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")

    # Validacao de venda: impede venda maior que a posicao atual
    if data.operation == OperationType.sell.value or data.operation == "sell":
        current_qty = _calc_current_quantity(db, portfolio_id, data.ticker.upper())
        if data.quantity > current_qty:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Quantidade insuficiente para venda. "
                    f"Posicao atual de {data.ticker.upper()}: {current_qty:.4f} "
                    f"| Tentativa de venda: {data.quantity:.4f}"
                ),
            )

    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=data.ticker.upper(),
        asset_type=data.asset_type,
        operation=data.operation,
        quantity=data.quantity,
        price=data.price,
        fees=data.fees or 0.0,
        date=data.date,
        currency=data.currency or "BRL",
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    logger.info("Transacao criada: id=%s ticker=%s op=%s qty=%s", tx.id, tx.ticker, tx.operation, tx.quantity)
    return TransactionOut.model_validate(tx)


def get_transaction(db: Session, tx_id: int, user_id: int) -> TransactionOut:
    tx = (
        db.query(Transaction)
        .join(Portfolio, Portfolio.id == Transaction.portfolio_id)
        .filter(Transaction.id == tx_id, Portfolio.user_id == user_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada")
    return TransactionOut.model_validate(tx)


def list_transactions(
    db: Session,
    portfolio_id: int,
    user_id: int,
    ticker: str | None = None,
    asset_type: str | None = None,
    operation: str | None = None,
    year: int | None = None,
) -> list[TransactionOut]:
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")

    filters = [Transaction.portfolio_id == portfolio_id]
    if ticker:
        filters.append(Transaction.ticker == ticker.upper())
    if asset_type:
        filters.append(Transaction.asset_type == asset_type)
    if operation:
        filters.append(Transaction.operation == operation)
    if year:
        filters.append(extract("year", Transaction.date) == year)

    rows = (
        db.query(Transaction)
        .filter(and_(*filters))
        .order_by(Transaction.date.desc())
        .all()
    )
    return [TransactionOut.model_validate(t) for t in rows]


def update_transaction(
    db: Session,
    tx_id: int,
    user_id: int,
    data: TransactionUpdate,
) -> TransactionOut:
    tx = (
        db.query(Transaction)
        .join(Portfolio, Portfolio.id == Transaction.portfolio_id)
        .filter(Transaction.id == tx_id, Portfolio.user_id == user_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada")

    update_data = data.model_dump(exclude_unset=True)
    if "ticker" in update_data:
        update_data["ticker"] = update_data["ticker"].upper()
    for field, value in update_data.items():
        setattr(tx, field, value)

    db.commit()
    db.refresh(tx)
    logger.info("Transacao atualizada: id=%s", tx.id)
    return TransactionOut.model_validate(tx)


def delete_transaction(db: Session, tx_id: int, user_id: int) -> None:
    tx = (
        db.query(Transaction)
        .join(Portfolio, Portfolio.id == Transaction.portfolio_id)
        .filter(Transaction.id == tx_id, Portfolio.user_id == user_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada")
    db.delete(tx)
    db.commit()
    logger.info("Transacao removida: id=%s", tx_id)
