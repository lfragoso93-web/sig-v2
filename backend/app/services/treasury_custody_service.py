"""DB-first Treasury custody-date projection under the disclosed D+2 policy."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_calendar_service import add_certified_business_days


TREASURY_STANDARD_MARKET = "TESOURO_DIRETO_STANDARD"


async def resolve_conservative_treasury_custody_date(
    db: AsyncSession,
    *,
    transaction_date: date,
    market: str = TREASURY_STANDARD_MARKET,
) -> date:
    """Return D+2 using only certified daily facts persisted for the market.

    Missing coverage raises ``MarketCalendarCoverageError``. The caller must
    surface that state instead of treating a weekday, projected holiday, or
    provider response as a confirmed custody date.
    """
    return await add_certified_business_days(
        db,
        market=market,
        start=transaction_date,
        count=2,
    )
