from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.integrations.brapi_dividends import sync_dividends_for_portfolio

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/proventos/{portfolio_id}")
async def sync_proventos(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id).first()
    if not p:
        raise HTTPException(404, "Carteira não encontrada")

    background_tasks.add_task(sync_dividends_for_portfolio, db, portfolio_id)
    return {"message": "Sincronização de proventos iniciada em background"}
