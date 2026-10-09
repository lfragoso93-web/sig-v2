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
        assert job_ids == {
            "persist_daily_close_prices",
            "persist_treasury_daily_close",
            "portfolio_snapshot_auto_maintenance",
            "update_quotes_intraday_full_hour",
            "update_quotes_intraday_half_hour",
        }

        intraday = scheduler.get_job("update_quotes_intraday_full_hour")
        assert intraday is not None
        assert isinstance(intraday.trigger, CronTrigger)

        friday = datetime(2026, 7, 10, 18, 1, tzinfo=scheduler.timezone)
        next_run = intraday.trigger.get_next_fire_time(None, friday)

        assert next_run.weekday() == 0
        assert next_run.hour == 9
        assert next_run.minute == 0
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
