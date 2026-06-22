from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, verify_password, decode_token,
)
from app.core.token_blacklist import blacklist_token, is_blacklisted
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
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
    await limiter.check(request, settings.LOGIN_RATE_LIMIT)

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


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Troca um refresh token valido por um novo par access + refresh.
    O refresh token usado e invalidado imediatamente (rotation).
    """
    payload = decode_token(data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado.",
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token sem jti — faca login novamente.",
        )

    if await is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token ja utilizado ou revogado.",
        )

    # Invalida o token atual imediatamente (rotation — evita reuso)
    await blacklist_token(jti, payload["exp"])

    user_id = payload["sub"]
    user = await get_user_by_email(db, None, user_id=int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado ou inativo.",
        )

    new_access  = create_access_token(subject=user_id)
    new_refresh = create_refresh_token(subject=user_id)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest):
    """
    Revoga o refresh token enviado.
    O cliente deve descartar access + refresh tokens localmente.
    Nao exige autenticacao — qualquer token valido pode ser revogado.
    """
    payload = decode_token(data.refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti")
        if jti:
            await blacklist_token(jti, payload["exp"])
    # Sempre retorna 204 — nao revela se o token era valido ou nao
