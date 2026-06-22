from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.integrations.brapi_dividends import sync_dividends_for_portfolio

router = APIRouter(tags=["sync"])


@router.post("/proventos/{portfolio_id}")
async def sync_proventos(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Carteira não encontrada")
    background_tasks.add_task(sync_dividends_for_portfolio, db, portfolio_id)
    return {"message": "Sincronização de proventos iniciada em background"}
