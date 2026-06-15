from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.treasury import TreasuryCreate, TreasuryResponse
from app.services.treasury_service import (
    create_treasury,
    list_treasury,
    delete_treasury,
)

router = APIRouter(prefix="/portfolios/{portfolio_id}/treasury", tags=["treasury"])


@router.get("/", response_model=list[TreasuryResponse])
async def list_treasury_investments(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_treasury(db, portfolio_id, current_user.id)


@router.post("/", response_model=TreasuryResponse, status_code=status.HTTP_201_CREATED)
async def add_treasury(
    portfolio_id: int,
    data: TreasuryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_treasury(db, portfolio_id, current_user.id, data)


@router.delete("/{treasury_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_treasury(
    portfolio_id: int,
    treasury_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await delete_treasury(db, treasury_id, portfolio_id, current_user.id)
    return None
