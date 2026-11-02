"""Account-scoped throttling for password reset email requests."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections import deque

from fastapi import HTTPException, status

from app.core.cache import get_redis
from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

MAX_REQUESTS = 2
WINDOW_SECONDS = 120
LOCKOUT_SECONDS = 60 * 60

_memory_windows: dict[str, deque[float]] = {}
_memory_lockouts: dict[str, float] = {}

_REGISTER_REQUEST_LUA = """
local locked_ttl = redis.call('TTL', KEYS[2])
if locked_ttl > 0 then
  return {0, locked_ttl}
end
local now = redis.call('TIME')
local now_ms = now[1] * 1000 + math.floor(now[2] / 1000)
local oldest_ms = now_ms - tonumber(ARGV[1]) * 1000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', oldest_ms)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[2]) then
  redis.call('SET', KEYS[2], 'locked', 'EX', ARGV[3])
  redis.call('DEL', KEYS[1], KEYS[3])
  return {0, tonumber(ARGV[3])}
end
local sequence = redis.call('INCR', KEYS[3])
redis.call('ZADD', KEYS[1], now_ms, tostring(now_ms) .. ':' .. tostring(sequence))
redis.call('EXPIRE', KEYS[1], ARGV[1])
redis.call('EXPIRE', KEYS[3], ARGV[1])
return {1, 0}
"""


def _account_key(email: str) -> str:
    normalized = email.strip().lower().encode("utf-8")
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), normalized, hashlib.sha256
    ).hexdigest()
    return f"auth:password-reset:{digest}"


def _too_many_requests(retry_after: int) -> HTTPException:
    minutes = max(1, (retry_after + 59) // 60)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "Limite de solicitações de recuperação atingido. "
            f"Tente novamente em aproximadamente {minutes} minuto(s)."
        ),
        headers={"Retry-After": str(max(1, retry_after))},
    )


async def register_password_reset_request(email: str) -> None:
    """Allow two requests per account in two minutes, then lock for one hour."""
    key = _account_key(email)
    redis_client = await get_redis()
    if redis_client is not None:
        try:
            allowed, retry_after = await redis_client.eval(
                _REGISTER_REQUEST_LUA,
                3,
                f"{key}:window",
                f"{key}:lock",
                f"{key}:sequence",
                WINDOW_SECONDS,
                MAX_REQUESTS,
                LOCKOUT_SECONDS,
            )
            if int(allowed) != 1:
                raise _too_many_requests(int(retry_after))
            return
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(
                "Falha ao aplicar limite de reset via Redis: %s",
                sanitize_log_value(exc),
            )
            if settings.ENVIRONMENT.strip().lower() == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Recuperação de senha temporariamente indisponível.",
                ) from exc
    elif settings.ENVIRONMENT.strip().lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recuperação de senha temporariamente indisponível.",
        )

    now = time.monotonic()
    locked_until = _memory_lockouts.get(key, 0)
    if locked_until > now:
        raise _too_many_requests(int(locked_until - now))
    _memory_lockouts.pop(key, None)
    requests = _memory_windows.setdefault(key, deque())
    while requests and requests[0] <= now - WINDOW_SECONDS:
        requests.popleft()
    requests.append(now)
    if len(requests) > MAX_REQUESTS:
        _memory_windows.pop(key, None)
        _memory_lockouts[key] = now + LOCKOUT_SECONDS
        raise _too_many_requests(LOCKOUT_SECONDS)


async def clear_password_reset_lockout(email: str) -> None:
    """Clear both the one-hour lock and its rolling request counter."""
    key = _account_key(email)
    redis_client = await get_redis()
    if redis_client is not None:
        try:
            await redis_client.delete(f"{key}:window", f"{key}:lock")
        except Exception as exc:
            logger.warning(
                "Falha ao limpar limite de reset via Redis: %s",
                sanitize_log_value(exc),
            )
            if settings.ENVIRONMENT.strip().lower() == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Não foi possível desbloquear o usuário agora.",
                ) from exc
    elif settings.ENVIRONMENT.strip().lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível desbloquear o usuário agora.",
        )

    _memory_windows.pop(key, None)
    _memory_lockouts.pop(key, None)
