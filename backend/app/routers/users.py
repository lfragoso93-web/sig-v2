import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserPasswordUpdate, UserResponse, UserUpdate
from app.schemas.auth import MessageResponse
from app.services.email_service import (
    send_account_deleted_email,
    send_password_changed_email,
)
from app.services.user_service import update_user, delete_user

logger = logging.getLogger(__name__)

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
    try:
        await send_password_changed_email(
            current_user.email,
            current_user.name or current_user.email,
            origin="alteração nas configurações da conta",
        )
    except Exception as exc:
        logger.warning("Falha ao enviar aviso de senha alterada: %s", exc)
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
    email = current_user.email
    name = current_user.name or current_user.email
    await delete_user(db, current_user.id)
    try:
        await send_account_deleted_email(email, name)
    except Exception as exc:
        logger.warning("Falha ao enviar e-mail de exclusão de conta: %s", exc)
    return MessageResponse(message="Conta excluida com sucesso")
