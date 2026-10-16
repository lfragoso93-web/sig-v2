"""Resolve B3 calendar audit configuration from database and environment."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.b3_market_calendar import validate_b3_source_url
from app.services.config_service import get_config


B3_CALENDAR_SOURCE_URL_KEY = "market_calendar.b3_source_url"
B3_CALENDAR_SOURCE_YEAR_KEY = "market_calendar.b3_source_year"


@dataclass(frozen=True)
class B3MarketCalendarAuditConfiguration:
    source_url: str
    source_year: int
    source_origin: str


async def resolve_b3_market_calendar_audit_configuration(
    db: AsyncSession,
    *,
    runtime_settings: Settings,
) -> B3MarketCalendarAuditConfiguration:
    """Prefer non-empty SuperAdmin values, otherwise use the environment."""
    configured_url = (
        await get_config(db, B3_CALENDAR_SOURCE_URL_KEY) or ""
    ).strip()
    configured_year = (
        await get_config(db, B3_CALENDAR_SOURCE_YEAR_KEY) or ""
    ).strip()
    source_url = configured_url or (
        runtime_settings.B3_MARKET_CALENDAR_SOURCE_URL or ""
    )
    raw_year = configured_year or str(
        runtime_settings.B3_MARKET_CALENDAR_SOURCE_YEAR or ""
    )
    try:
        source_year = int(raw_year)
    except ValueError as exc:
        raise ValueError("B3 calendar source year must be an integer") from exc
    validate_b3_source_url(source_url)
    if not 2000 <= source_year <= 2100:
        raise ValueError("B3 calendar source year must be valid")
    origin = (
        "system_config" if configured_url or configured_year else "environment"
    )
    return B3MarketCalendarAuditConfiguration(
        source_url=source_url,
        source_year=source_year,
        source_origin=origin,
    )
