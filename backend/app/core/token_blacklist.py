"""
Blacklist de tokens (refresh e reset) com suporte a Redis e fallback em memoria.

Design:
- Chave de token individual: jti (UUID unico por token) -> exp (epoch UTC)
- Chave de revogacao global de sessoes por usuario: user_id -> timestamp (epoch float)
- Expurgo lazy em memoria: tokens vencidos sao removidos a cada insercao.
- Integrado ao Redis (SETEX) quando disponivel para persistencia entre workers.
"""
import asyncio
import logging
import time
from typing import Any, Dict

from app.core.cache import get_redis
from app.core.config import settings
from app.core.security import monotonic_timestamp

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_store: Dict[str, float] = {}  # jti -> exp (epoch UTC)
_user_revoked_at: Dict[int, float] = {}  # user_id -> monotonic_timestamp


def _jti_redis_key(jti: str) -> str:
    return f"auth:blacklist:jti:{jti}"


def _user_revoked_redis_key(user_id: int) -> str:
    return f"auth:blacklist:user_revoked:{user_id}"


def _purge_expired() -> None:
    """Remove entradas ja vencidas. Chamar dentro do lock."""
    now = time.time()
    expired = [jti for jti, exp in _store.items() if exp <= now]
    for jti in expired:
        del _store[jti]


async def blacklist_token(jti: str, exp: float) -> None:
    """Adiciona jti a blacklist (Redis + memoria) ate seu horario de expiracao."""
    if not jti:
        return
    exp_float = float(exp)
    ttl_seconds = max(1, int(exp_float - time.time()) + 5)

    redis_client = await get_redis()
    if redis_client:
        try:
            await redis_client.set(
                _jti_redis_key(jti), str(exp_float), ex=ttl_seconds
            )
        except Exception as exc:
            logger.warning("Falha ao gravar blacklist de token no Redis: %s", exc)

    async with _lock:
        _purge_expired()
        _store[jti] = exp_float


async def is_blacklisted(jti: str) -> bool:
    """Retorna True se o jti estiver na blacklist e ainda nao tiver vencido."""
    if not jti:
        return True

    redis_client = await get_redis()
    if redis_client:
        try:
            cached = await redis_client.get(_jti_redis_key(jti))
            if cached is not None:
                return True
        except Exception as exc:
            logger.warning("Falha ao consultar blacklist no Redis: %s", exc)

    async with _lock:
        exp = _store.get(jti)
        if exp is None:
            return False
        if time.time() > exp:
            del _store[jti]
            return False
        return True


async def revoke_user_sessions(user_id: int) -> float:
    """Revoga todos os tokens emitidos para user_id ate o instante atual."""
    revoked_ts = monotonic_timestamp()
    ttl_seconds = max(3600, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    redis_client = await get_redis()
    if redis_client:
        try:
            await redis_client.set(
                _user_revoked_redis_key(user_id),
                f"{revoked_ts:.6f}",
                ex=ttl_seconds,
            )
        except Exception as exc:
            logger.warning(
                "Falha ao gravar revogacao de sessao no Redis (user_id=%s): %s",
                user_id,
                exc,
            )

    async with _lock:
        _user_revoked_at[int(user_id)] = revoked_ts
    return revoked_ts


async def is_user_session_revoked(
    user_id: int, payload: Dict[str, Any]
) -> bool:
    """Verifica se o token foi emitido antes da ultima revogacao de senha do usuario."""
    revoked_ts: float | None = None

    redis_client = await get_redis()
    if redis_client:
        try:
            raw = await redis_client.get(_user_revoked_redis_key(int(user_id)))
            if raw is not None:
                revoked_ts = float(raw)
        except Exception as exc:
            logger.warning(
                "Falha ao consultar revogacao de sessao no Redis: %s", exc
            )

    async with _lock:
        mem_ts = _user_revoked_at.get(int(user_id))
        if mem_ts is not None:
            revoked_ts = max(revoked_ts or 0.0, mem_ts)

    if revoked_ts is None:
        return False

    token_ts = payload.get("iat_ts")
    if token_ts is None:
        token_ts = payload.get("iat", 0.0)
    return float(token_ts) <= revoked_ts


async def blacklist_size() -> int:
    """Retorna tamanho atual da blacklist em memoria (util para debug/monitoramento)."""
    async with _lock:
        _purge_expired()
        return len(_store)
