from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, verify_password,
)
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate
from app.services.user_service import get_user_by_email, create_user

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o administrador.",
        )

    # Migração silenciosa de hash legado (passlib) para bcrypt v5 nativo.
    # Se o hash atual não começa com o prefixo padrao do bcrypt nativo puro,
    # re-hasheia na hora do login bem-sucedido sem impacto para o usuário.
    try:
        import bcrypt as _bcrypt
        _bcrypt.checkpw(data.password.encode(), user.hashed_password.encode())
    except Exception:
        # Hash legado detectado — re-hasheia com bcrypt v5
        user.hashed_password = hash_password(data.password)
        await db.commit()

    access_token  = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Cadastro público. Usa UserCreate (name obrigatório, min 8 chars na senha).
    Delega para create_user que já valida e-mail duplicado.
    """
    user = await create_user(db, data)
    access_token  = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
