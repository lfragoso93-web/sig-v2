from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from app.services.rentabilidade_service import (
    _latest_snapshot,
    flush_rentabilidade_cache,
)


@pytest.mark.asyncio
async def test_latest_snapshot_uses_explicit_utc_policy():
    db = AsyncMock()
    expected = object()

    with (
        patch(
            "app.services.rentabilidade_service.utc_today",
            return_value=date(2026, 8, 1),
        ),
        patch(
            "app.services.rentabilidade_service._snapshot_at",
            new=AsyncMock(return_value=expected),
        ) as snapshot_at,
    ):
        result = await _latest_snapshot(db, 7)

    assert result is expected
    snapshot_at.assert_awaited_once_with(db, 7, date(2026, 8, 1))


@pytest.mark.asyncio
async def test_cache_flush_logs_failure_and_continues(caplog):
    cache_delete = AsyncMock(side_effect=[RuntimeError("redis down"), None, None])

    with patch(
        "app.services.rentabilidade_service.cache_delete",
        new=cache_delete,
    ):
        await flush_rentabilidade_cache(7)

    assert cache_delete.await_count == 3
    assert "falha ao invalidar cache 7/kpis" in caplog.text
