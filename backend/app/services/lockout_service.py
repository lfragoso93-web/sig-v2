"""Servico de protecao contra forca bruta (Account Lockout).

Bloqueia temporariamente contas com mais de 5 tentativas consecutivas
de login com falha em um intervalo de 15 minutos via Redis (ou memoria).
"""

import logging
import time
from fastapi import HTTPException, status
from app.core.cache import get_redis

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutos

_memory_failed_attempts: dict[str, tuple[int, float]] = {}
_memory_lockouts: dict[str, float] = {}


def _failed_key(email: str) -> str:
    return f"auth:failed:{email.strip().lower()}"


def _lockout_key(email: str) -> str:
    return f"auth:lockout:{email.strip().lower()}"


def _clean_memory(email_key: str) -> None:
    now = time.time()
    if email_key in _memory_failed_attempts:
        _, exp = _memory_failed_attempts[email_key]
        if now > exp:
            del _memory_failed_attempts[email_key]
    if email_key in _memory_lockouts:
        exp = _memory_lockouts[email_key]
        if now > exp:
            del _memory_lockouts[email_key]


async def check_lockout(email: str) -> None:
    """Verifica se o usuario esta bloqueado por tentativas excessivas."""
    email_clean = email.strip().lower()
    redis_client = await get_redis()
    if redis_client:
        try:
            locked_ttl = await redis_client.ttl(_lockout_key(email_clean))
            if locked_ttl and locked_ttl > 0:
                minutes = (locked_ttl // 60) + 1
                logger.warning(
                    "Tentativa de login bloqueada para %s (restam %ds)",
                    email_clean,
                    locked_ttl,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Conta temporariamente bloqueada por excesso de "
                        f"tentativas. Tente novamente em {minutes} minuto(s)."
                    ),
                )
            return
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Falha ao consultar lockout no Redis: %s", exc)

    _clean_memory(email_clean)
    if email_clean in _memory_lockouts:
        exp = _memory_lockouts[email_clean]
        remaining = int(exp - time.time())
        if remaining > 0:
            minutes = (remaining // 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Conta temporariamente bloqueada por excesso de "
                    f"tentativas. Tente novamente em {minutes} minuto(s)."
                ),
            )


async def register_failed_attempt(email: str) -> None:
    """Registra falha de autenticacao e ativa lockout se exceder o limite."""
    email_clean = email.strip().lower()
    redis_client = await get_redis()
    if redis_client:
        try:
            f_key = _failed_key(email_clean)
            attempts = await redis_client.incr(f_key)
            if attempts == 1:
                await redis_client.expire(f_key, LOCKOUT_DURATION_SECONDS)

            if attempts >= MAX_FAILED_ATTEMPTS:
                l_key = _lockout_key(email_clean)
                await redis_client.set(
                    l_key, "locked", ex=LOCKOUT_DURATION_SECONDS
                )
                await redis_client.delete(f_key)
                logger.warning(
                    "Conta %s bloqueada por %d segundos apos %d falhas.",
                    email_clean,
                    LOCKOUT_DURATION_SECONDS,
                    attempts,
                )
            return
        except Exception as exc:
            logger.warning("Falha ao registrar tentativa no Redis: %s", exc)

    now = time.time()
    _clean_memory(email_clean)
    attempts, _ = _memory_failed_attempts.get(
        email_clean, (0, now + LOCKOUT_DURATION_SECONDS)
    )
    attempts += 1
    if attempts >= MAX_FAILED_ATTEMPTS:
        _memory_lockouts[email_clean] = now + LOCKOUT_DURATION_SECONDS
        _memory_failed_attempts.pop(email_clean, None)
    else:
        _memory_failed_attempts[email_clean] = (
            attempts,
            now + LOCKOUT_DURATION_SECONDS,
        )


async def clear_lockout(email: str) -> None:
    """Limpa contadores de falha apos login bem-sucedido."""
    email_clean = email.strip().lower()
    redis_client = await get_redis()
    if redis_client:
        try:
            await redis_client.delete(
                _failed_key(email_clean), _lockout_key(email_clean)
            )
        except Exception as exc:
            logger.warning("Falha ao limpar lockout no Redis: %s", exc)

    _memory_failed_attempts.pop(email_clean, None)
    _memory_lockouts.pop(email_clean, None)
