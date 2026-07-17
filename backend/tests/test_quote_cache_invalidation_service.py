from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services import quote_cache_invalidation_service as service


@pytest.mark.asyncio
async def test_invalidates_summary_and_positions_for_affected_portfolios(monkeypatch) -> None:
    rows = [SimpleNamespace(portfolio_id=3), SimpleNamespace(portfolio_id=8)]
    result = SimpleNamespace(all=lambda: rows)
    db = AsyncMock()
    db.execute.return_value = result
    cache_delete = AsyncMock()
    monkeypatch.setattr(service, "cache_delete", cache_delete)

    invalidated = await service.invalidate_quote_consumers(db, [AssetType.ACAO])

    assert invalidated == 2
    assert cache_delete.await_count == 4
    cache_delete.assert_any_await("portfolio:3:summary")
    cache_delete.assert_any_await("portfolio:3:positions")
    cache_delete.assert_any_await("portfolio:8:summary")
    cache_delete.assert_any_await("portfolio:8:positions")


@pytest.mark.asyncio
async def test_refresh_invalidates_only_after_quote_update(monkeypatch) -> None:
    update = AsyncMock(return_value=12)
    invalidate = AsyncMock(return_value=2)
    monkeypatch.setattr(service, "invalidate_quote_consumers", invalidate)

    import app.services.quotes_service as quotes_service
    monkeypatch.setattr(quotes_service, "update_all_quotes", update)

    db = AsyncMock()
    result = await service.refresh_quotes_and_invalidate(db, [AssetType.FII])

    assert result == (12, 2)
    update.assert_awaited_once_with(db, asset_types=[AssetType.FII])
    invalidate.assert_awaited_once_with(db, asset_types=[AssetType.FII])
