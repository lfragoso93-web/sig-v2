from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import jwt
import jwt.exceptions
import bcrypt
from app.core.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica senha contra hash bcrypt.

    Compatibilidade com hashes legados gerados pelo passlib:
    - passlib usava prefixo '$2b$' mas com cost factor e salt no formato
      ligeiramente diferente em algumas versoes, resultando em hashes que
      bcrypt>=4.x nao consegue verificar diretamente.
    - Tentativa 1: verificacao normal com bcrypt nativo.
    - Tentativa 2: se o hash comeca com '$2b$', tenta tambem com prefixo
      '$2y$' (formato PHP/passlib antigo) para maxima compatibilidade.
    - Retorna False silenciosamente em qualquer erro de formato.
    """
    try:
        plain_bytes  = plain.encode("utf-8")
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        pass

    # Fallback: tenta prefixo alternativo para hashes passlib legados
    try:
        plain_bytes = plain.encode("utf-8")
        if hashed.startswith("$2b$"):
            alt = ("$2y$" + hashed[4:]).encode("utf-8")
            return bcrypt.checkpw(plain_bytes, alt)
        if hashed.startswith("$2y$"):
            alt = ("$2b$" + hashed[4:]).encode("utf-8")
            return bcrypt.checkpw(plain_bytes, alt)
    except Exception:
        pass

    return False


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire, "type": token_type}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Cria refresh token com jti (UUID) para suporte a blacklist."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # identificador unico para blacklist
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.exceptions.InvalidTokenError:
        return None
