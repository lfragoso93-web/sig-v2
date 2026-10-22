"""Servico de protecao contra forca bruta (Account Lockout).

Bloqueia temporariamente contas com mais de 5 tentativas consecutivas
de login com falha em um intervalo de 15 minutos via Redis.
"""

import logging
from fastapi import HTTPException, status
from app.core.cache import get_redis

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutos


def _failed_key(email: str) -> str:
    return f"auth:failed:{email.strip().lower()}"


def _lockout_key(email: str) -> str:
    return f"auth:lockout:{email.strip().lower()}"


async def check_lockout(email: str) -> None:
    """Verifica se o usuario esta bloqueado por tentativas excessivas."""
    redis_client = await get_redis()
    if not redis_client:
        return

    try:
        locked_ttl = await redis_client.ttl(_lockout_key(email))
        if locked_ttl and locked_ttl > 0:
            minutes = (locked_ttl // 60) + 1
            logger.warning(
                "Tentativa de login bloqueada para %s (restam %ds)",
                email,
                locked_ttl,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Conta temporariamente bloqueada por excesso de "
                    f"tentativas. Tente novamente em {minutes} minuto(s)."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Falha ao consultar lockout no Redis: %s", exc)


async def register_failed_attempt(email: str) -> None:
    """Registra falha de autenticacao e ativa lockout se exceder o limite."""
    redis_client = await get_redis()
    if not redis_client:
        return

    try:
        f_key = _failed_key(email)
        attempts = await redis_client.incr(f_key)
        if attempts == 1:
            await redis_client.expire(f_key, LOCKOUT_DURATION_SECONDS)

        if attempts >= MAX_FAILED_ATTEMPTS:
            l_key = _lockout_key(email)
            await redis_client.set(
                l_key, "locked", ex=LOCKOUT_DURATION_SECONDS
            )
            await redis_client.delete(f_key)
            logger.warning(
                "Conta %s bloqueada por %d segundos apos %d falhas.",
                email,
                LOCKOUT_DURATION_SECONDS,
                attempts,
            )
    except Exception as exc:
        logger.warning("Falha ao registrar tentativa no Redis: %s", exc)


async def clear_lockout(email: str) -> None:
    """Limpa contadores de falha apos login bem-sucedido."""
    redis_client = await get_redis()
    if not redis_client:
        return

    try:
        await redis_client.delete(_failed_key(email), _lockout_key(email))
    except Exception as exc:
        logger.warning("Falha ao limpar lockout no Redis: %s", exc)
