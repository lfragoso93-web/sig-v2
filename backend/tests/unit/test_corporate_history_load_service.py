from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import corporate_history_load_service as service
from app.services.corporate_history_load_service import CorporateHistoryState

STATE_BEFORE = CorporateHistoryState(10, 2, 4, 0, 6)
STATE_AFTER = CorporateHistoryState(12, 3, 5, 0, 7)


class NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def _db():
    return SimpleNamespace(
        begin_nested=lambda: NestedTransaction(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )


def _reconciliation():
    return SimpleNamespace(
        matched=2,
        conflicts=0,
        unreconciled=1,
        canonical=2,
        suppressed_equivalents=1,
    )


async def _configure(monkeypatch, *, sync_error: Exception | None = None):
    inspect = AsyncMock(side_effect=[STATE_BEFORE, STATE_AFTER])
    lock = AsyncMock()
    assets = (SimpleNamespace(id=1, ticker="PETR4"),)
    load_assets = AsyncMock(return_value=assets)
    sync = AsyncMock(
        side_effect=sync_error,
        return_value=[SimpleNamespace(id=99)] if sync_error is None else None,
    )
    reconcile = AsyncMock(return_value=_reconciliation())
    monkeypatch.setattr(service, "inspect_corporate_history_state", inspect)
    monkeypatch.setattr(service, "_acquire_lock", lock)
    monkeypatch.setattr(service, "load_corporate_history_assets", load_assets)
    monkeypatch.setattr(service, "sync_corporate_events_for_asset", sync)
    monkeypatch.setattr(service, "reconcile_corporate_events_for_asset", reconcile)
    return sync, reconcile


@pytest.mark.asyncio
async def test_dry_run_reports_projected_state_and_always_rolls_back(
    monkeypatch,
) -> None:
    sync, reconcile = await _configure(monkeypatch)
    db = _db()

    result = await service.run_corporate_history_load(
        run_id="20260731-190000",
        date_from=date(2000, 1, 1),
        date_to=date(2026, 7, 31),
        dry_run=True,
        db=db,
    )

    assert result.ok is True
    assert result.transaction_state == "dry_run_rolled_back"
    assert result.committed is False
    assert result.before == STATE_BEFORE
    assert result.projected_after == STATE_AFTER
    assert result.events_created == 1
    assert result.reconciliation["matched"] == 2
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    sync.assert_awaited_once()
    reconcile.assert_awaited_once_with(db, 1)


@pytest.mark.asyncio
async def test_apply_commits_only_when_every_asset_succeeds(monkeypatch) -> None:
    await _configure(monkeypatch)
    db = _db()

    result = await service.run_corporate_history_load(
        run_id="20260731-190001",
        date_from=date(2000, 1, 1),
        date_to=date(2026, 7, 31),
        dry_run=False,
        db=db,
    )

    assert result.ok is True
    assert result.transaction_state == "committed"
    assert result.committed is True
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_asset_failure_is_reported_and_rolls_back_whole_run(monkeypatch) -> None:
    await _configure(monkeypatch, sync_error=RuntimeError("provider offline"))
    db = _db()

    result = await service.run_corporate_history_load(
        run_id="20260731-190002",
        date_from=date(2000, 1, 1),
        date_to=date(2026, 7, 31),
        dry_run=False,
        db=db,
    )

    assert result.ok is False
    assert result.transaction_state == "rolled_back"
    assert result.errors == (
        {
            "ticker": "PETR4",
            "type": "RuntimeError",
            "message": "provider offline",
        },
    )
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_window_fails_before_database_access() -> None:
    db = _db()

    with pytest.raises(ValueError, match="date_from"):
        await service.run_corporate_history_load(
            run_id="20260731-190003",
            date_from=date(2026, 7, 31),
            date_to=date(2000, 1, 1),
            dry_run=True,
            db=db,
        )

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
