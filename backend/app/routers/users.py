from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserPasswordUpdate, UserResponse, UserUpdate
from app.schemas.auth import MessageResponse
from app.services.user_service import update_user, delete_user

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_user(db, current_user.id, data)


@router.patch("/me/password", response_model=MessageResponse)
async def change_my_password(
    data: UserPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual invalida",
        )

    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return MessageResponse(message="Senha alterada com sucesso")


@router.patch("/me/onboarding", response_model=UserResponse)
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca o onboarding do usuario autenticado como concluido."""
    return await update_user(db, current_user.id, UserUpdate(onboarding_completed=True))


@router.delete("/me", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    O usuario exclui a propria conta permanentemente.
    Remove todos os dados associados via ON DELETE CASCADE no PostgreSQL.
    """
    await delete_user(db, current_user.id)
    return MessageResponse(message="Conta excluida com sucesso")
