import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from app.services.user_service import get_user_by_email
from datetime import timedelta

logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRE_MINUTES = 30

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="E-mail ou senha incorretos",
)


async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    # Normaliza o email para evitar falhas por caixa ou espacos
    email_normalizado = data.email.strip().lower()

    user = await get_user_by_email(db, email_normalizado)
    if not user:
        logger.warning("Login falhou: e-mail nao encontrado (%s)", email_normalizado)
        raise _INVALID_CREDENTIALS

    try:
        senha_ok = verify_password(data.password, user.hashed_password)
    except Exception as exc:
        # Hash corrompido ou esquema incompativel — nao vaza informacao ao cliente
        logger.error("Erro ao verificar senha do usuario id=%s: %s", user.id, exc)
        raise _INVALID_CREDENTIALS from exc

    if not senha_ok:
        logger.warning("Login falhou: senha invalida para usuario id=%s", user.id)
        raise _INVALID_CREDENTIALS

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inativo. Entre em contato com o administrador.",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado",
        )
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado ou inativo")
    return create_access_token(str(user.id))


async def forgot_password(db: AsyncSession, email: str) -> str:
    """
    Gera um token de reset de senha valido por 30 minutos.
    Nao revela se o e-mail existe ou nao para evitar enumeracao.
    """
    user = await get_user_by_email(db, email.strip().lower())
    if not user or not user.is_active:
        return "usuario-nao-encontrado-token-invalido"

    reset_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        token_type="reset",
    )
    return reset_token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    """Valida o token de reset e atualiza a senha do usuario."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nova senha deve ter no minimo 8 caracteres",
        )
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(hashed_password=hash_password(new_password))
    )
    await db.flush()
