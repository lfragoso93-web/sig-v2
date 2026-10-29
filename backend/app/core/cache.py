import json
import logging
import time

import redis.asyncio as redis  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_redis_unavailable_until: float = 0.0


async def get_redis() -> redis.Redis | None:
    global _redis_client, _redis_unavailable_until
    if _redis_client is not None:
        return _redis_client

    if time.time() < _redis_unavailable_until:
        return None

    try:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await _redis_client.ping()
        logger.info("Redis conectado com sucesso")
    except Exception as exc:
        logger.warning(
            "Redis indisponivel - cache desativado: %s: %s",
            type(exc).__name__,
            sanitize_log_value(exc),
        )
        _redis_client = None
        _redis_unavailable_until = time.time() + 10.0
    return _redis_client


async def cache_get(key: str) -> dict | None:
    client = await get_redis()
    if not client:
        return None
    try:
        data = await client.get(key)
        return json.loads(data) if data else None
    except Exception as exc:
        logger.warning(
            "Falha ao ler cache key=%s: %s: %s",
            sanitize_log_value(key),
            type(exc).__name__,
            sanitize_log_value(exc),
        )
        return None


async def cache_set(key: str, value: dict, ttl: int = 300) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.warning(
            "Falha ao escrever cache key=%s: %s: %s",
            sanitize_log_value(key),
            type(exc).__name__,
            sanitize_log_value(exc),
        )


async def cache_delete(key: str) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.delete(key)
    except Exception as exc:
        logger.warning(
            "Falha ao excluir cache key=%s: %s: %s",
            sanitize_log_value(key),
            type(exc).__name__,
            sanitize_log_value(exc),
        )


async def cache_delete_pattern(pattern: str) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        batch: list[str] = []
        async for key in client.scan_iter(match=pattern, count=100):
            batch.append(key)
            if len(batch) >= 500:
                await client.delete(*batch)
                batch.clear()
        if batch:
            await client.delete(*batch)
    except Exception as exc:
        logger.warning(
            "Falha ao excluir cache pattern=%s: %s: %s",
            sanitize_log_value(pattern),
            type(exc).__name__,
            sanitize_log_value(exc),
        )
