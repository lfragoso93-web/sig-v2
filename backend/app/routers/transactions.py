from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.transaction_service import (
    create_transaction, list_transactions, delete_transaction
)

router = APIRouter(prefix="/api/v1", tags=["transactions"])


@router.post("/portfolios/{portfolio_id}/transactions", response_model=TransactionOut, status_code=201)
def create(
    portfolio_id: int,
    body: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body.portfolio_id = portfolio_id
    return create_transaction(db, portfolio_id, current_user.id, body)


@router.get("/portfolios/{portfolio_id}/transactions", response_model=list[TransactionOut])
def list_tx(
    portfolio_id: int,
    ticker: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    tx_type: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_transactions(db, portfolio_id, current_user.id, ticker, asset_type, tx_type, year)


@router.delete("/transactions/{tx_id}", status_code=204)
def delete(
    tx_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_transaction(db, tx_id, current_user.id)
