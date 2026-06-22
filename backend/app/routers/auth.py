from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, verify_password,
)
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate
from app.services.user_service import get_user_by_email, create_user

router = APIRouter(tags=["auth"])


def _get_limiter():
    """Importa o limiter do main sem circular import."""
    from app.main import limiter
    return limiter


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Autenticacao por e-mail e senha.
    Rate limit: LOGIN_RATE_LIMIT (default 10/minute) por IP.
    Respostas 401/403 intencionalmente genericas para nao confirmar existencia de conta.
    """
    limiter = _get_limiter()
    await limiter.check(request, settings.LOGIN_RATE_LIMIT)  # levanta RateLimitExceeded -> 429

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

    # Migracao silenciosa de hash legado (passlib) para bcrypt v5 nativo.
    try:
        import bcrypt as _bcrypt
        _bcrypt.checkpw(data.password.encode(), user.hashed_password.encode())
    except Exception:
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
async def register(request: Request, data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Cadastro publico.
    Rate limit: REGISTER_RATE_LIMIT (default 5/minute) por IP.
    """
    limiter = _get_limiter()
    await limiter.check(request, settings.REGISTER_RATE_LIMIT)

    user = await create_user(db, data)
    access_token  = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
