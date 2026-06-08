from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.user import UserUpdate, UserResponse
from app.schemas.auth import MessageResponse
from app.services.user_service import update_user_profile
from app.core.security import hash_password, verify_password
from fastapi import HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user=Depends(get_current_user)):
    """Perfil do usuário logado."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza nome e avatar do usuário logado."""
    return await update_user_profile(db, current_user, data)


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Altera a senha do usuário logado."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="Nova senha deve ter no mínimo 8 caracteres")
    current_user.hashed_password = hash_password(data.new_password)
    await db.flush()
    return MessageResponse(message="Senha alterada com sucesso")
