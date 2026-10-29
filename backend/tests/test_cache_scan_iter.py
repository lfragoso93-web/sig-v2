import pytest
from unittest.mock import AsyncMock, patch
from app.core.cache import cache_delete_pattern


@pytest.mark.asyncio
async def test_cache_delete_pattern_uses_scan_iter():
    mock_redis = AsyncMock()

    async def async_generator(match, count):
        for key in ["portfolio:1", "portfolio:2", "portfolio:3"]:
            yield key

    mock_redis.scan_iter = async_generator

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        await cache_delete_pattern("portfolio:*")
        mock_redis.delete.assert_awaited_once_with("portfolio:1", "portfolio:2", "portfolio:3")


@pytest.mark.asyncio
async def test_cache_delete_pattern_batches_large_keysets():
    mock_redis = AsyncMock()

    async def async_generator(match, count):
        for i in range(1050):
            yield f"key:{i}"

    mock_redis.scan_iter = async_generator

    with patch("app.core.cache.get_redis", return_value=mock_redis):
        await cache_delete_pattern("key:*")
        # 500 + 500 + 50 = 3 batches
        assert mock_redis.delete.await_count == 3
