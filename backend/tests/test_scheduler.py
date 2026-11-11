from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from apscheduler.triggers.cron import CronTrigger

import app.core.scheduler as scheduler_module
from app.core.scheduler import scheduler, start_scheduler


@pytest.mark.asyncio
async def test_scheduler_registers_only_price_and_local_maintenance_jobs():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    start_scheduler()

    try:
        job_ids = {job.id for job in scheduler.get_jobs()}
        expected = {
            "persist_daily_close_prices",
            "persist_treasury_daily_close",
            "portfolio_snapshot_auto_maintenance",
            "update_quotes_intraday_full_hour",
            "update_crypto_quotes_offhours_weekdays",
            "update_crypto_quotes_weekends",
            "refresh_asset_fundamentals_daily",
            "sync_asset_dividends_morning",
            "sync_corporate_events_daily",
        }
        if scheduler_module.settings.ENABLE_DAILY_BENCHMARK_SYNC:
            expected.add("sync_benchmark_rates_daily")
            expected.add("sync_ibov_benchmark_daily")
        if scheduler_module.settings.ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT:
            expected.add("audit_b3_market_calendar_monthly")
        expected.add("notify_daily_dividend_payments")
        assert job_ids == expected

        snapshots = scheduler.get_job("portfolio_snapshot_auto_maintenance")
        assert snapshots is not None
        saturday_after_close = datetime(2026, 7, 11, 21, 1, tzinfo=scheduler.timezone)
        next_snapshot_run = snapshots.trigger.get_next_fire_time(
            None, saturday_after_close
        )
        assert next_snapshot_run.weekday() == 6
        assert (next_snapshot_run.hour, next_snapshot_run.minute) == (21, 0)

        intraday = scheduler.get_job("update_quotes_intraday_full_hour")
        assert intraday is not None
        assert isinstance(intraday.trigger, CronTrigger)

        friday = datetime(2026, 7, 10, 18, 1, tzinfo=scheduler.timezone)
        next_run = intraday.trigger.get_next_fire_time(None, friday)

        assert next_run.weekday() == 0
        assert next_run.hour == 9
        assert next_run.minute == 0

        dividends = scheduler.get_job("sync_asset_dividends_morning")
        assert dividends is not None
        saturday_morning = datetime(2026, 7, 10, 8, 1, tzinfo=scheduler.timezone)
        next_dividend_run = dividends.trigger.get_next_fire_time(
            None, saturday_morning
        )
        assert next_dividend_run.weekday() == 5
        assert (next_dividend_run.hour, next_dividend_run.minute) == (8, 0)

        corporate_events = scheduler.get_job("sync_corporate_events_daily")
        assert corporate_events is not None
        next_event_run = corporate_events.trigger.get_next_fire_time(
            None,
            datetime(2026, 7, 10, 22, 1, tzinfo=scheduler.timezone),
        )
        assert next_event_run.weekday() == 0
        assert (next_event_run.hour, next_event_run.minute) == (22, 0)

        if scheduler_module.settings.ENABLE_DAILY_BENCHMARK_SYNC:
            benchmarks = scheduler.get_job("sync_benchmark_rates_daily")
            assert benchmarks is not None
            next_benchmark_run = benchmarks.trigger.get_next_fire_time(
                None,
                datetime(2026, 7, 10, 7, 0, tzinfo=scheduler.timezone),
            )
            assert (next_benchmark_run.hour, next_benchmark_run.minute) == (
                8,
                40,
            )
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_scheduler_registers_opt_in_monthly_b3_calendar_audit(
    monkeypatch,
):
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()
    monkeypatch.setattr(
        scheduler_module.settings,
        "ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT",
        True,
    )

    start_scheduler()

    try:
        job = scheduler.get_job("audit_b3_market_calendar_monthly")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)
        next_run = job.trigger.get_next_fire_time(
            None,
            datetime(2026, 7, 2, tzinfo=scheduler.timezone),
        )
        assert next_run.day == 1
        assert next_run.hour == 8
        assert next_run.minute == 15
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_monthly_b3_audit_skips_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()
    monkeypatch.setattr(
        scheduler_module.settings,
        "ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT",
        True,
    )

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "audit_b3_market_calendar",
            "period": "monthly",
            "ttl_seconds": 300,
        }
        yield False

    audit = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.b3_market_calendar_audit_service."
        "run_b3_market_calendar_monthly_audit",
        audit,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("audit_b3_market_calendar_monthly")
        assert job is not None
        await job.func()
        audit.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_daily_close_skips_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "persist_daily_close_prices",
            "period": "daily",
            "ttl_seconds": 7200,
        }
        yield False

    backfill = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.asset_price_global_backfill_service."
        "run_global_asset_price_backfill",
        backfill,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("persist_daily_close_prices")
        assert job is not None
        await job.func()
        backfill.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_intraday_quotes_skip_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "update_quotes_intraday",
            "period": "intraday",
            "ttl_seconds": 7200,
        }
        yield False

    refresh = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.quote_cache_invalidation_service.refresh_quotes_and_invalidate",
        refresh,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("update_quotes_intraday_full_hour")
        assert job is not None
        await job.func()
        refresh.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_crypto_offhours_quotes_skip_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "update_quotes_intraday",
            "period": "intraday",
            "ttl_seconds": 7200,
            "status_job_name": "update_crypto_quotes",
        }
        yield False

    refresh = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.quote_cache_invalidation_service.refresh_quotes_and_invalidate",
        refresh,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("update_crypto_quotes_weekends")
        assert job is not None
        await job.func()
        refresh.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_treasury_daily_close_skips_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "persist_treasury_daily_close",
            "period": "daily",
            "ttl_seconds": 7200,
        }
        yield False

    history = AsyncMock()
    latest = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.treasury_price_history_service.import_treasury_price_history",
        history,
    )
    monkeypatch.setattr(
        "app.services.treasury_price_history_service.update_treasury_latest_prices",
        latest,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("persist_treasury_daily_close")
        assert job is not None
        await job.func()
        history.assert_not_awaited()
        latest.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_snapshot_maintenance_skips_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "portfolio_snapshot_auto_maintenance",
            "period": "daily",
            "ttl_seconds": 7200,
        }
        yield False

    maintenance = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.portfolio_snapshot_twr_maintenance_service."
        "maintain_twr_snapshots_for_active_portfolios",
        maintenance,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("portfolio_snapshot_auto_maintenance")
        assert job is not None
        await job.func()
        maintenance.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_asset_fundamentals_daily_skips_work_when_distributed_lock_is_refused(
    monkeypatch,
) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def refused_lock(**kwargs):
        assert kwargs == {
            "job_name": "refresh_asset_fundamentals_daily",
            "period": "daily",
            "ttl_seconds": 7200,
        }
        yield False

    refresh_mock = AsyncMock()
    monkeypatch.setattr(scheduler_module, "distributed_job_lock", refused_lock)
    monkeypatch.setattr(
        "app.services.asset_fundamentals_refresh_service.run_asset_fundamentals_refresh",
        refresh_mock,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("refresh_asset_fundamentals_daily")
        assert job is not None
        await job.func()
        refresh_mock.assert_not_awaited()
    finally:
        scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_daily_close_runs_daily_and_uses_zero_end_grace(monkeypatch) -> None:
    from types import SimpleNamespace

    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    @asynccontextmanager
    async def acquired_lock(**kwargs):
        yield True

    class _FakeScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return SimpleNamespace(all=lambda: self._rows)

    class _FakeSessionCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, stmt):
            sql = str(stmt)
            if "asset_type =" in sql:
                return _FakeScalarResult(["BTC"])
            return _FakeScalarResult(["NVDA", "BTC", "AREA11"])

    class _FrozenDatetime:
        current = datetime(2026, 11, 11, 20, 45)

        @classmethod
        def now(cls, tz=None):
            return cls.current.replace(tzinfo=tz)

    backfill_calls = []

    async def fake_backfill(**kwargs):
        backfill_calls.append(kwargs)
        return {"audited": 3, "inserted": 3, "errors": 0}

    monkeypatch.setattr(scheduler_module, "distributed_job_lock", acquired_lock)
    monkeypatch.setattr(scheduler_module, "datetime", _FrozenDatetime)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", _FakeSessionCtx)
    monkeypatch.setattr(
        "app.services.asset_price_global_backfill_service.run_global_asset_price_backfill",
        fake_backfill,
    )
    start_scheduler()

    try:
        job = scheduler.get_job("persist_daily_close_prices")
        assert job is not None
        saturday_after_close = datetime(2026, 7, 11, 20, 46, tzinfo=scheduler.timezone)
        next_run = job.trigger.get_next_fire_time(None, saturday_after_close)
        assert next_run.weekday() == 6

        await job.func()
        assert len(backfill_calls) == 1
        weekday_call = backfill_calls[0]
        assert weekday_call["full_history"] is False
        assert weekday_call["end_grace_days"] == 0
        assert weekday_call["include_start_gaps"] is False
        assert weekday_call["asset_types"] is None
        assert weekday_call["tickers"] == {"NVDA", "BTC", "AREA11"}

        _FrozenDatetime.current = datetime(2026, 11, 14, 20, 45)
        await job.func()
        assert len(backfill_calls) == 2
        weekend_call = backfill_calls[1]
        assert weekend_call["asset_types"] == {"CRIPTO"}
        assert weekend_call["tickers"] == {"BTC"}
    finally:
        scheduler.shutdown(wait=False)
