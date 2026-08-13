from datetime import datetime

import pytest
from apscheduler.triggers.cron import CronTrigger

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
