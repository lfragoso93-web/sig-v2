"""DB-first access to certified market calendars."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_calendar_day import MarketCalendarDay


class MarketCalendarCoverageError(RuntimeError):
    pass


async def add_certified_business_days(
    db: AsyncSession, *, market: str, start: date, count: int
) -> date:
    """Advance using only persisted, source-qualified calendar facts."""
    if count < 1:
        raise ValueError("calendar business-day count must be positive")
    rows = await db.execute(
        select(MarketCalendarDay.calendar_date, MarketCalendarDay.is_business_day)
        .where(MarketCalendarDay.market == market, MarketCalendarDay.calendar_date > start)
        .order_by(MarketCalendarDay.calendar_date.asc())
    )
    expected = start + timedelta(days=1)
    found = 0
    for calendar_date, is_business_day in rows.all():
        while expected < calendar_date:
            raise MarketCalendarCoverageError(
                f"market calendar coverage missing for {market}:{expected.isoformat()}"
            )
        if is_business_day:
            found += 1
            if found == count:
                return calendar_date
        expected = calendar_date + timedelta(days=1)
    raise MarketCalendarCoverageError(
        f"market calendar coverage missing for {market} after {start.isoformat()}"
    )
