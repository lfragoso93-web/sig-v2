"""Recurring read-only verification of the configured B3 annual calendar."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.integrations.b3_market_calendar import fetch_b3_annual_calendar_page
from app.services.b3_market_calendar_dry_run import (
    B3MarketCalendarDryRunReport,
    extract_b3_annual_calendar_dry_run,
)


@dataclass(frozen=True)
class B3MarketCalendarAuditResult:
    """Read-only monthly audit outcome for structured scheduler logs."""

    report: B3MarketCalendarDryRunReport
    source_sha256: str


async def run_b3_market_calendar_monthly_audit(
    *,
    source_url: str,
    source_year: int,
) -> B3MarketCalendarAuditResult:
    """Fetch and report a B3 source without writing calendar facts."""
    source_text = await fetch_b3_annual_calendar_page(source_url)
    report = extract_b3_annual_calendar_dry_run(
        source_text,
        year=source_year,
        source_reference=source_url,
    )
    return B3MarketCalendarAuditResult(
        report=report,
        source_sha256=sha256(source_text.encode("utf-8")).hexdigest(),
    )
