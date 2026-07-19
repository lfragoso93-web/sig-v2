from datetime import datetime

import pytest
from apscheduler.triggers.cron import CronTrigger

from app.core.scheduler import (
    HELD_MARKET_PIPELINE_EVENT_OPTIONS,
    scheduler,
    start_scheduler,
)


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
    finally:
        scheduler.shutdown(wait=False)


def test_market_pipeline_does_not_collect_or_materialize_events():
    assert HELD_MARKET_PIPELINE_EVENT_OPTIONS == {
        "sync_events": False,
        "materialize": False,
    }
