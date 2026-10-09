"""Read-only extraction of explicit B3 holiday calendar facts.

The annual B3 calendar is a source snapshot, not a substitute for later
operational notices.  This module deliberately produces only the dates that
the supplied source explicitly describes as closed; it never infers a complete
business-day calendar and never writes to the database.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re
from typing import Any


_PORTUGUESE_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_DATE_PATTERN = re.compile(
    r"(?P<day>\d{1,2})\s+de\s+(?P<month>"
    + "|".join(_PORTUGUESE_MONTHS)
    + r")\b",
    re.IGNORECASE,
)
_SHARED_MONTH_DATE_RANGE_PATTERN = re.compile(
    r"(?P<first_day>\d{1,2})\s+e\s+(?P<second_day>\d{1,2})\s+de\s+"
    + r"(?P<month>"
    + "|".join(_PORTUGUESE_MONTHS)
    + r")\b",
    re.IGNORECASE,
)
_NORMAL_OPERATION_MARKERS = ("funcionamento normal", "opera normalmente")
_SPECIAL_OPERATION_MARKERS = ("horário especial", "horario especial")


@dataclass(frozen=True)
class B3MarketCalendarDryRunReport:
    """A source-auditable, non-persistent B3 annual-calendar extraction."""

    schema_version: str
    market: str
    year: int
    source: str
    source_reference: str
    dry_run: bool
    database_writes_executed: int
    source_dates_found: tuple[str, ...]
    explicitly_closed_dates: tuple[str, ...]
    special_operation_dates: tuple[str, ...]
    complete_daily_coverage: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_b3_annual_calendar_dry_run(
    source_text: str,
    *,
    year: int,
    source_reference: str,
    market: str = "TESOURO_DIRETO_STANDARD",
) -> B3MarketCalendarDryRunReport:
    """Extract explicit closed dates from a supplied official B3 source.

    A date is considered closed only when its source line does not say that B3
    operates normally or with a special schedule. The result intentionally has
    incomplete daily coverage: populating ordinary dates needs a reviewed,
    source-specific certification step and any subsequent B3 notices.
    """
    if not source_text.strip():
        raise ValueError("B3 calendar source text cannot be empty")
    if not source_reference.strip():
        raise ValueError("B3 calendar source reference cannot be empty")

    found: set[date] = set()
    closed: set[date] = set()
    special: set[date] = set()

    def classify(calendar_date: date, normalized_line: str) -> None:
        found.add(calendar_date)
        normal_operation = any(
            marker in normalized_line
            for marker in _NORMAL_OPERATION_MARKERS
        )
        if normal_operation:
            return
        special_operation = any(
            marker in normalized_line
            for marker in _SPECIAL_OPERATION_MARKERS
        )
        if special_operation:
            special.add(calendar_date)
            return
        closed.add(calendar_date)

    for line in source_text.splitlines():
        normalized_line = line.casefold()
        range_matches = _SHARED_MONTH_DATE_RANGE_PATTERN.finditer(
            normalized_line
        )
        for match in range_matches:
            month = _PORTUGUESE_MONTHS[match.group("month")]
            for group in ("first_day", "second_day"):
                calendar_date = date(year, month, int(match.group(group)))
                classify(calendar_date, normalized_line)
        for match in _DATE_PATTERN.finditer(normalized_line):
            calendar_date = date(
                year,
                _PORTUGUESE_MONTHS[match.group("month")],
                int(match.group("day")),
            )
            classify(calendar_date, normalized_line)

    if not found:
        raise ValueError(
            "B3 calendar source text contains no recognized Portuguese dates"
        )

    def format_dates(values: set[date]) -> tuple[str, ...]:
        return tuple(day.isoformat() for day in sorted(values))

    return B3MarketCalendarDryRunReport(
        schema_version="b3-market-calendar-dry-run.v1",
        market=market,
        year=year,
        source="B3_ANNUAL_CALENDAR",
        source_reference=source_reference,
        dry_run=True,
        database_writes_executed=0,
        source_dates_found=format_dates(found),
        explicitly_closed_dates=format_dates(closed),
        special_operation_dates=format_dates(special),
        complete_daily_coverage=False,
    )
