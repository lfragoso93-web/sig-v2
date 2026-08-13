from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dividend import DividendResponse
from app.services.dividend_service import list_dividends

router = APIRouter(tags=["dividends"])


@router.get("/{portfolio_id}/dividends", response_model=list[DividendResponse])
async def get_dividends(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await list_dividends(db, portfolio_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
