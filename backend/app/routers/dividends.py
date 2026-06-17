from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.dividend import DividendCreate, DividendResponse
from app.services.dividend_service import (
    create_dividend,
    list_dividends,
    delete_dividend,
)

router = APIRouter(tags=["dividends"])


@router.get("/{portfolio_id}/dividends", response_model=list[DividendResponse])
async def get_dividends(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_dividends(db, portfolio_id, current_user.id)


@router.post("/{portfolio_id}/dividends", response_model=DividendResponse, status_code=status.HTTP_201_CREATED)
async def add_dividend(
    portfolio_id: int,
    data: DividendCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_dividend(db, portfolio_id, current_user.id, data)


@router.delete("/{portfolio_id}/dividends/{dividend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dividend(
    portfolio_id: int,
    dividend_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await delete_dividend(db, dividend_id, portfolio_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provento nao encontrado")
    return None
