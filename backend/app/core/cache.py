import json
import logging
from typing import Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)
_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        try:
            import redis.asyncio as aioredis
            _redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        except Exception as e:
            logger.error(f"[Cache] Falha ao conectar Redis: {e}")
            return None
    return _redis


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    r = await get_redis()
    if not r:
        return False
    try:
        await r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.error(f"[Cache] Erro ao setar {key}: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    if not r:
        return None
    try:
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.error(f"[Cache] Erro ao buscar {key}: {e}")
        return None


async def cache_delete(key: str) -> bool:
    r = await get_redis()
    if not r:
        return False
    try:
        await r.delete(key)
        return True
    except Exception as e:
        return False


async def cache_flush_pattern(pattern: str) -> int:
    r = await get_redis()
    if not r:
        return 0
    try:
        keys = await r.keys(pattern)
        return await r.delete(*keys) if keys else 0
    except Exception as e:
        logger.error(f"[Cache] Erro ao flush {pattern}: {e}")
        return 0
