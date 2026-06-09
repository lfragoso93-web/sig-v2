from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.portfolio_service import recalc_positions

router = APIRouter(prefix="/portfolios/{portfolio_id}/transactions", tags=["transactions"])


def _get_portfolio(portfolio_id: int, user: User, db: Session) -> Portfolio:
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira n\u00e3o encontrada.")
    return p


@router.get("", response_model=List[TransactionOut])
def list_transactions(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, current_user, db)
    return (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.desc())
        .all()
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    portfolio_id: int,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, current_user, db)

    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=payload.ticker.upper(),
        asset_type=payload.asset_type,
        operation=payload.operation,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees or 0.0,
        date=payload.date,
        notes=payload.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # Recalcula pre\u00e7o m\u00e9dio e posi\u00e7\u00f5es
    recalc_positions(portfolio_id, db)

    return tx


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, current_user, db)

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.portfolio_id == portfolio_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transa\u00e7\u00e3o n\u00e3o encontrada.")

    db.delete(tx)
    db.commit()

    recalc_positions(portfolio_id, db)
