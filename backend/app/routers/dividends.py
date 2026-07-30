from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
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
    return await list_dividends(db, portfolio_id, current_user.id)
