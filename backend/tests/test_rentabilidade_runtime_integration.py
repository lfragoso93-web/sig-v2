from unittest.mock import AsyncMock, patch

import pytest

from app.services.rentabilidade_cache_service import invalidate_rentabilidade_cache


@pytest.mark.asyncio
async def test_cache_invalidation_logs_failure_and_continues(caplog):
    cache_delete = AsyncMock(side_effect=[RuntimeError("redis down"), None, None])

    with patch(
        "app.services.rentabilidade_cache_service.cache_delete",
        new=cache_delete,
    ):
        await invalidate_rentabilidade_cache(7)

    assert cache_delete.await_count == 3
    assert "falha ao invalidar cache 7/kpis" in caplog.text
