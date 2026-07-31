from datetime import datetime

import pytest
from app.core.scheduler import (
    CORPORATE_EVENTS_SCHEDULER_ENABLED,
    HELD_MARKET_PIPELINE_EVENT_OPTIONS,
    PROVENTOS_SYNC_ONLY_HELD,
    run_scheduled_corporate_event_sync,
    scheduler,
    start_scheduler,
)
from apscheduler.triggers.cron import CronTrigger


@pytest.mark.asyncio
async def test_proventos_scheduler_has_one_weekday_event_job():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    start_scheduler()

    try:
        assert scheduler.get_job("sync_daily_proventos_morning") is None

        evening = scheduler.get_job("sync_daily_proventos_evening")
        assert evening is not None
        assert isinstance(evening.trigger, CronTrigger)

        friday = datetime(2026, 7, 10, 18, 11, tzinfo=scheduler.timezone)
        next_run = evening.trigger.get_next_fire_time(None, friday)

        assert next_run.weekday() == 0
        assert next_run.hour == 18
        assert next_run.minute == 10

        corporate = scheduler.get_job("sync_corporate_events_incremental")
        assert corporate is not None
        corporate_run = corporate.trigger.get_next_fire_time(None, friday)
        assert corporate_run.weekday() == 4
        assert corporate_run.hour == 18
        assert corporate_run.minute == 35
    finally:
        scheduler.shutdown(wait=False)


def test_market_pipeline_does_not_collect_or_materialize_events():
    assert HELD_MARKET_PIPELINE_EVENT_OPTIONS == {
        "sync_events": False,
    }


def test_proventos_scheduler_collects_the_global_catalog():
    assert PROVENTOS_SYNC_ONLY_HELD is False


def test_corporate_scheduler_is_safe_by_default_until_migration():
    assert CORPORATE_EVENTS_SCHEDULER_ENABLED is False


@pytest.mark.asyncio
async def test_disabled_corporate_scheduler_returns_without_database_access():
    assert await run_scheduled_corporate_event_sync() is None
