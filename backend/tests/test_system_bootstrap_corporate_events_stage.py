from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import system_bootstrap_corporate_events_stage as stage
from app.services.system_bootstrap_execution_context import (
    SystemBootstrapExecutionContext,
)


_CONTEXT = SystemBootstrapExecutionContext(
    run_id="20260808-000000",
    branch="stable-15jun",
    commit_sha="a" * 40,
)


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _assets_result(*assets):
    scalars = MagicMock()
    scalars.all.return_value = list(assets)
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_corporate_events_stage_is_blocked_before_opening_session(monkeypatch):
    monkeypatch.delenv(stage.CORPORATE_EVENTS_BOOTSTRAP_AUTH_ENV, raising=False)
    session_factory = MagicMock()
    monkeypatch.setattr(stage, "AsyncSessionLocal", session_factory)

    with pytest.raises(stage.SystemBootstrapCorporateEventsGateError):
        await stage.run_system_bootstrap_corporate_events_stage(_CONTEXT)

    session_factory.assert_not_called()


@pytest.mark.asyncio
async def test_corporate_events_stage_locks_before_query_and_commits(monkeypatch):
    asset_a = SimpleNamespace(id=1, ticker="AAA3", asset_type="ACAO")
    asset_b = SimpleNamespace(id=2, ticker="BBB34", asset_type="BDR")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[MagicMock(), _assets_result(asset_a, asset_b)])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    monkeypatch.setattr(stage, "AsyncSessionLocal", lambda: _SessionContext(db))

    sync = AsyncMock(side_effect=[[object()], [object(), object()]])
    monkeypatch.setattr(stage, "sync_corporate_events_for_asset", sync)

    detail = await stage.run_system_bootstrap_corporate_events_stage(
        _CONTEXT,
        authorized=True,
    )

    assert db.execute.await_count == 2
    first_call = db.execute.await_args_list[0]
    assert "pg_advisory_xact_lock" in str(first_call.args[0])
    assert first_call.args[1] == {"lock_key": stage.CORPORATE_EVENTS_ADVISORY_LOCK_KEY}
    sync.assert_any_await(db, asset_a)
    sync.assert_any_await(db, asset_b)
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    assert detail == "processed=2 created=3 skipped=0"


@pytest.mark.asyncio
async def test_corporate_events_stage_filters_supported_types_in_db_query(monkeypatch):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[MagicMock(), _assets_result()])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    monkeypatch.setattr(stage, "AsyncSessionLocal", lambda: _SessionContext(db))
    sync = AsyncMock()
    monkeypatch.setattr(stage, "sync_corporate_events_for_asset", sync)

    await stage.run_system_bootstrap_corporate_events_stage(_CONTEXT, authorized=True)

    query = db.execute.await_args_list[1].args[0]
    compiled = str(query)
    assert "assets.asset_type" in compiled
    assert "IN" in compiled
    assert stage.SUPPORTED_CORPORATE_EVENT_ASSET_TYPES == (
        "ACAO",
        "BDR",
        "ETF_NACIONAL",
    )
    sync.assert_not_awaited()


@pytest.mark.asyncio
async def test_corporate_events_stage_rolls_back_and_stops_after_failure(monkeypatch):
    asset_a = SimpleNamespace(id=1, ticker="AAA3", asset_type="ACAO")
    asset_b = SimpleNamespace(id=2, ticker="BBB3", asset_type="ACAO")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[MagicMock(), _assets_result(asset_a, asset_b)])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    monkeypatch.setattr(stage, "AsyncSessionLocal", lambda: _SessionContext(db))

    failure = RuntimeError("provider failure")
    sync = AsyncMock(side_effect=failure)
    monkeypatch.setattr(stage, "sync_corporate_events_for_asset", sync)

    with pytest.raises(RuntimeError, match="provider failure"):
        await stage.run_system_bootstrap_corporate_events_stage(
            _CONTEXT,
            authorized=True,
        )

    sync.assert_awaited_once_with(db, asset_a)
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


def test_corporate_events_stage_report_is_deterministic():
    report = stage.CorporateEventsStageReport(
        assets_processed=7,
        events_created=11,
        assets_skipped=0,
    )

    assert report.to_detail() == "processed=7 created=11 skipped=0"
