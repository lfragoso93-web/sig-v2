from contextlib import asynccontextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.services.corporate_event_incremental_sync_service import (
    run_incremental_corporate_event_sync,
)


class FakeDb:
    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    @asynccontextmanager
    async def begin_nested(self):
        yield


@pytest.mark.asyncio
async def test_busy_history_lock_skips_without_writes():
    db = FakeDb()
    with (
        patch(
            "app.services.corporate_event_incremental_sync_service."
            "_acquire_incremental_lock",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.services.corporate_event_incremental_sync_service._load_assets",
            new=AsyncMock(),
        ) as load_assets,
    ):
        result = await run_incremental_corporate_event_sync(
            db,
            date_from=date(2026, 6, 1),
            date_to=date(2026, 7, 31),
        )

    assert result.skipped_reason == "corporate_history_lock_busy"
    assert result.committed is False
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    load_assets.assert_not_awaited()


@pytest.mark.asyncio
async def test_failure_isolated_per_asset_and_successes_are_committed():
    db = FakeDb()
    assets = (
        SimpleNamespace(id=1, ticker="ABCD3"),
        SimpleNamespace(id=2, ticker="FAIL3"),
    )
    report = SimpleNamespace(
        matched=1,
        conflicts=0,
        unreconciled=0,
        canonical=1,
        suppressed_equivalents=1,
    )
    sync = AsyncMock(side_effect=[[SimpleNamespace(id=10)], RuntimeError("provider")])

    with (
        patch(
            "app.services.corporate_event_incremental_sync_service."
            "_acquire_incremental_lock",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.corporate_event_incremental_sync_service._load_assets",
            new=AsyncMock(return_value=assets),
        ),
        patch(
            "app.services.corporate_event_incremental_sync_service."
            "sync_corporate_events_for_asset",
            new=sync,
        ),
        patch(
            "app.services.corporate_event_incremental_sync_service."
            "reconcile_corporate_events_for_asset",
            new=AsyncMock(return_value=report),
        ),
    ):
        result = await run_incremental_corporate_event_sync(
            db,
            date_from=date(2026, 6, 1),
            date_to=date(2026, 7, 31),
        )

    assert result.committed is True
    assert result.assets_scanned == 2
    assert result.assets_changed == 1
    assert result.assets_failed == 1
    assert result.events_created == 1
    assert result.reconciliation["matched"] == 1
    assert result.errors[0]["ticker"] == "FAIL3"
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_inverted_incremental_window():
    with pytest.raises(ValueError, match="date_from"):
        await run_incremental_corporate_event_sync(
            FakeDb(),
            date_from=date(2026, 8, 1),
            date_to=date(2026, 7, 31),
        )
