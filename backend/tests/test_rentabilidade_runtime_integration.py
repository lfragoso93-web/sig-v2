from unittest.mock import AsyncMock, patch

import pytest

from app.core import cache as cache_module
from app.services.rentabilidade_cache_service import (
    invalidate_rentabilidade_cache,
)


@pytest.mark.asyncio
async def test_cache_invalidation_logs_failure_and_continues(
    caplog,
):
    cache_delete = AsyncMock(
        side_effect=[RuntimeError("redis down"), None, None],
    )

    with patch(
        "app.services.rentabilidade_cache_service.cache_delete",
        new=cache_delete,
    ):
        await invalidate_rentabilidade_cache(7)

    assert cache_delete.await_count == 3
    assert "falha ao invalidar cache 7/kpis" in caplog.text


@pytest.mark.asyncio
async def test_redis_connection_failure_disables_cache_without_raising(
    caplog,
):
    redis_client = AsyncMock()
    redis_client.ping.side_effect = RuntimeError("redis down")
    cache_module._redis_client = None

    with patch("app.core.cache.redis.Redis", return_value=redis_client):
        client = await cache_module.get_redis()

    assert client is None
    assert cache_module._redis_client is None
    assert "Redis indisponivel - cache desativado" in caplog.text


@pytest.mark.asyncio
async def test_cache_operations_are_fail_open_when_redis_is_unavailable():
    cache_module._redis_client = None

    with patch("app.core.cache.get_redis", new=AsyncMock(return_value=None)):
        assert await cache_module.cache_get("rent:7:kpis") is None
        await cache_module.cache_set("rent:7:kpis", {"ok": True})
        await cache_module.cache_delete("rent:7:kpis")
        await cache_module.cache_delete_pattern("rent:7:*")
