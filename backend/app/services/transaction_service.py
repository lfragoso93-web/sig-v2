from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.portfolio import Portfolio
from app.schemas.transaction import TransactionCreate, TransactionOut
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


def _get_or_create_asset(db: Session, ticker: str, asset_type: str) -> Asset:
    asset = db.query(Asset).filter(Asset.ticker == ticker).first()
    if not asset:
        asset = Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type,
        )
        db.add(asset)
        db.flush()
    return asset


def _calc_average_price(db: Session, portfolio_id: int, asset_id: int) -> float:
    """Calcula preço médio ponderado após todas as compras (excluindo vendas)."""
    rows = (
        db.query(Transaction.transaction_type, Transaction.quantity, Transaction.price)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset_id,
        )
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    qty = 0.0
    cost = 0.0
    for r in rows:
        if r.transaction_type in (TransactionType.COMPRA, TransactionType.BONIFICACAO):
            qty += float(r.quantity)
            cost += float(r.quantity) * float(r.price)
        elif r.transaction_type == TransactionType.VENDA:
            sold = min(float(r.quantity), qty)
            if qty > 0:
                avg = cost / qty
                cost -= sold * avg
            qty -= sold
            qty = max(qty, 0)
            cost = max(cost, 0)

    return cost / qty if qty > 0 else 0.0


def create_transaction(db: Session, portfolio_id: int, user_id: int, data: TransactionCreate) -> TransactionOut:
    # Valida ownership
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id,
    ).first()
    if not portfolio:
        raise HTTPException(404, "Carteira não encontrada")

    asset = _get_or_create_asset(db, data.ticker, data.asset_type)

    total_value = data.quantity * data.price + (data.fees or 0)

    tx = Transaction(
        portfolio_id=portfolio_id,
        asset_id=asset.id,
        transaction_type=data.transaction_type,
        quantity=data.quantity,
        price=data.price,
        total_value=total_value,
        fees=data.fees or 0,
        transaction_date=data.transaction_date,
        broker=data.broker,
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    avg = _calc_average_price(db, portfolio_id, asset.id)

    return TransactionOut(
        id=tx.id,
        portfolio_id=tx.portfolio_id,
        ticker=asset.ticker,
        asset_type=asset.asset_type,
        transaction_type=tx.transaction_type,
        quantity=float(tx.quantity),
        price=float(tx.price),
        total_value=float(tx.total_value),
        fees=float(tx.fees),
        transaction_date=tx.transaction_date,
        broker=tx.broker,
        notes=tx.notes,
        average_price_after=avg,
    )


def list_transactions(
    db: Session, portfolio_id: int, user_id: int,
    ticker: str | None = None,
    asset_type: str | None = None,
    tx_type: str | None = None,
    year: int | None = None,
) -> list[TransactionOut]:
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id,
    ).first()
    if not portfolio:
        raise HTTPException(404, "Carteira não encontrada")

    filters = [Transaction.portfolio_id == portfolio_id]
    if ticker:
        filters.append(Asset.ticker == ticker.upper())
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if tx_type:
        filters.append(Transaction.transaction_type == tx_type)
    if year:
        from sqlalchemy import extract
        filters.append(extract("year", Transaction.transaction_date) == year)

    rows = (
        db.query(Transaction, Asset)
        .join(Asset, Asset.id == Transaction.asset_id)
        .filter(and_(*filters))
        .order_by(Transaction.transaction_date.desc())
        .all()
    )

    return [
        TransactionOut(
            id=t.id,
            portfolio_id=t.portfolio_id,
            ticker=a.ticker,
            asset_type=a.asset_type,
            transaction_type=t.transaction_type,
            quantity=float(t.quantity),
            price=float(t.price),
            total_value=float(t.total_value),
            fees=float(t.fees),
            transaction_date=t.transaction_date,
            broker=t.broker,
            notes=t.notes,
            average_price_after=None,
        )
        for t, a in rows
    ]


def delete_transaction(db: Session, tx_id: int, user_id: int) -> None:
    tx = (
        db.query(Transaction)
        .join(Portfolio, Portfolio.id == Transaction.portfolio_id)
        .filter(Transaction.id == tx_id, Portfolio.user_id == user_id)
        .first()
    )
    if not tx:
        raise HTTPException(404, "Transação não encontrada")
    db.delete(tx)
    db.commit()
