from datetime import datetime

import pytest
from apscheduler.triggers.cron import CronTrigger

from app.core.scheduler import scheduler, start_scheduler


@pytest.mark.asyncio
async def test_proventos_scheduler_runs_daily_at_9_and_after_18():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler.remove_all_jobs()

    start_scheduler()

    try:
        morning = scheduler.get_job("sync_daily_proventos_morning")
        evening = scheduler.get_job("sync_daily_proventos_evening")

        assert morning is not None
        assert evening is not None
        assert isinstance(morning.trigger, CronTrigger)
        assert isinstance(evening.trigger, CronTrigger)

        now = datetime(2026, 7, 7, 8, 0, tzinfo=scheduler.timezone)

        assert morning.trigger.get_next_fire_time(None, now).hour == 9
        assert morning.trigger.get_next_fire_time(None, now).minute == 0
        assert evening.trigger.get_next_fire_time(None, now).hour == 18
        assert evening.trigger.get_next_fire_time(None, now).minute == 10
    finally:
        scheduler.shutdown(wait=False)
