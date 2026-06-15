import redis.asyncio as redis
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await _redis_client.ping()
            logger.info("Redis conectado com sucesso")
        except Exception:
            logger.warning("Redis indisponível — cache desativado")
            _redis_client = None
    return _redis_client


async def cache_get(key: str) -> dict | None:
    client = await get_redis()
    if not client:
        return None
    try:
        data = await client.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


async def cache_set(key: str, value: dict, ttl: int = 300) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
    except Exception:
        pass
