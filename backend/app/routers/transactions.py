from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.schemas.auth import MessageResponse
from app.schemas.pagination import PaginatedResponse
from app.services.transaction_service import (
    create_transaction, list_transactions, delete_transaction
)
from app.services.portfolio_service import get_portfolio
import math

router = APIRouter()


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_transaction(
    portfolio_id: int,
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra uma transação e atualiza preço médio e posição automaticamente."""
    # Garante que a carteira pertence ao usuário
    await get_portfolio(db, portfolio_id, current_user.id)
    return await create_transaction(db, portfolio_id, data)


@router.get(
    "/{portfolio_id}/transactions",
    response_model=PaginatedResponse[TransactionResponse],
)
async def list_portfolio_transactions(
    portfolio_id: int,
    asset_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    transactions, total = await list_transactions(db, portfolio_id, asset_id, page, page_size)
    return PaginatedResponse(
        items=transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.delete(
    "/{portfolio_id}/transactions/{transaction_id}",
    response_model=MessageResponse,
)
async def remove_transaction(
    portfolio_id: int,
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove transação e reconstrói a posição do ativo do zero."""
    await get_portfolio(db, portfolio_id, current_user.id)
    await delete_transaction(db, transaction_id, portfolio_id)
    return MessageResponse(message="Transação removida e posição recalculada")
