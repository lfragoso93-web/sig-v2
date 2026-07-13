from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.csv_snapshot_rebuild_service import (
    rebuild_snapshots_after_csv_import,
)


class _SessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_rebuild_uses_first_transaction_date_and_refreshes_caches():
    db = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = date(2024, 1, 15)
    db.execute.return_value = query_result

    with (
        patch(
            "app.services.csv_snapshot_rebuild_service.AsyncSessionLocal",
            return_value=_SessionContext(db),
        ),
        patch(
            "app.services.csv_snapshot_rebuild_service.invalidate_snapshots_from",
            new=AsyncMock(return_value=12),
        ) as invalidate,
        patch(
            "app.services.csv_snapshot_rebuild_service.backfill_snapshots_with_returns",
            new=AsyncMock(return_value=400),
        ) as backfill,
        patch(
            "app.services.csv_snapshot_rebuild_service.invalidate_portfolio_cache",
            new=AsyncMock(),
        ) as invalidate_cache,
        patch(
            "app.services.csv_snapshot_rebuild_service.flush_rentabilidade_cache",
            new=AsyncMock(),
        ) as flush_cache,
    ):
        await rebuild_snapshots_after_csv_import(7)

    invalidate.assert_awaited_once_with(
        db,
        7,
        date(2024, 1, 15),
        commit=True,
    )
    backfill.assert_awaited_once_with(db, 7)
    invalidate_cache.assert_awaited_once_with(7)
    flush_cache.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_rebuild_skips_when_portfolio_has_no_transactions():
    db = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None
    db.execute.return_value = query_result

    with (
        patch(
            "app.services.csv_snapshot_rebuild_service.AsyncSessionLocal",
            return_value=_SessionContext(db),
        ),
        patch(
            "app.services.csv_snapshot_rebuild_service.invalidate_snapshots_from",
            new=AsyncMock(),
        ) as invalidate,
        patch(
            "app.services.csv_snapshot_rebuild_service.backfill_snapshots_with_returns",
            new=AsyncMock(),
        ) as backfill,
    ):
        await rebuild_snapshots_after_csv_import(9)

    invalidate.assert_not_awaited()
    backfill.assert_not_awaited()
