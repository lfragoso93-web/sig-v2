"""Build fail-closed, non-persistent market-calendar promotion plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from hashlib import sha256
import json
import re
from typing import Any


_CANDIDATE_SCHEMA_VERSION = "market-calendar-candidate.v1"
_PLAN_SCHEMA_VERSION = "market-calendar-promotion-plan.v1"
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class MarketCalendarSourceDocument:
    reference: str
    sha256: str


@dataclass(frozen=True)
class MarketCalendarCandidateDay:
    calendar_date: date
    is_business_day: bool
    source_reference: str


@dataclass(frozen=True)
class MarketCalendarPromotionPlan:
    schema_version: str
    dry_run: bool
    database_writes_executed: int
    candidate_sha256: str
    market: str
    year: int
    source_documents: tuple[MarketCalendarSourceDocument, ...]
    expected_days: int
    supplied_days: int
    blockers: tuple[str, ...]

    @property
    def promotable(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_documents"] = [
            asdict(document) for document in self.source_documents
        ]
        payload["blockers"] = list(self.blockers)
        payload["promotable"] = self.promotable
        return payload


def _parse_candidate_day(raw: object) -> MarketCalendarCandidateDay:
    if not isinstance(raw, dict):
        raise ValueError("calendar candidate day must be an object")
    try:
        calendar_date = date.fromisoformat(str(raw["date"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("calendar candidate day requires ISO date") from exc
    is_business_day = raw.get("is_business_day")
    if not isinstance(is_business_day, bool):
        raise ValueError(
            "calendar candidate day requires boolean is_business_day"
        )
    source_reference = str(raw.get("source_reference") or "").strip()
    if not source_reference:
        raise ValueError("calendar candidate day requires source_reference")
    return MarketCalendarCandidateDay(
        calendar_date=calendar_date,
        is_business_day=is_business_day,
        source_reference=source_reference,
    )


def _parse_source_document(raw: object) -> MarketCalendarSourceDocument:
    if not isinstance(raw, dict):
        raise ValueError("calendar source document must be an object")
    reference = str(raw.get("reference") or "").strip()
    digest = str(raw.get("sha256") or "").strip().lower()
    if not reference:
        raise ValueError("calendar source document requires reference")
    if not _SHA256_PATTERN.fullmatch(digest):
        raise ValueError("calendar source document requires SHA-256")
    return MarketCalendarSourceDocument(reference=reference, sha256=digest)


def _days_in_year(year: int) -> tuple[date, ...]:
    if not 2000 <= year <= 2100:
        raise ValueError("calendar candidate year must be valid")
    current = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    days: list[date] = []
    while current < end:
        days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def build_market_calendar_promotion_plan(
    candidate: dict[str, object],
) -> MarketCalendarPromotionPlan:
    """Validate a reviewed daily candidate without reading or writing the DB.

    The candidate is the complete human-reviewed input for a later executor.
    """
    if candidate.get("schema_version") != _CANDIDATE_SCHEMA_VERSION:
        raise ValueError("unsupported market calendar candidate schema")
    market = str(candidate.get("market") or "").strip()
    if not market:
        raise ValueError("calendar candidate requires market")
    try:
        year = int(candidate["year"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("calendar candidate requires year") from exc

    raw_sources = candidate.get("source_documents")
    raw_days = candidate.get("days")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("calendar candidate requires source_documents")
    if not isinstance(raw_days, list):
        raise ValueError("calendar candidate requires days")

    documents = tuple(_parse_source_document(raw) for raw in raw_sources)
    days = tuple(_parse_candidate_day(raw) for raw in raw_days)
    expected_dates = set(_days_in_year(year))
    source_references = {document.reference for document in documents}
    blockers: list[str] = []

    if len(source_references) != len(documents):
        blockers.append("duplicate_source_reference")

    days_by_date: dict[date, MarketCalendarCandidateDay] = {}
    for candidate_day in days:
        if candidate_day.calendar_date not in expected_dates:
            blockers.append(
                "day_outside_candidate_year:"
                f"{candidate_day.calendar_date.isoformat()}"
            )
            continue
        if candidate_day.source_reference not in source_references:
            blockers.append(
                "unknown_source_reference:"
                f"{candidate_day.calendar_date.isoformat()}"
            )
        if candidate_day.calendar_date in days_by_date:
            blockers.append(
                "duplicate_calendar_date:"
                f"{candidate_day.calendar_date.isoformat()}"
            )
            continue
        days_by_date[candidate_day.calendar_date] = candidate_day

    missing_dates = sorted(expected_dates - set(days_by_date))
    if missing_dates:
        blockers.append(
            "incomplete_daily_coverage:"
            "missing="
            f"{len(missing_dates)}:first={missing_dates[0].isoformat()}"
        )

    candidate_bytes = json.dumps(
        candidate,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return MarketCalendarPromotionPlan(
        schema_version=_PLAN_SCHEMA_VERSION,
        dry_run=True,
        database_writes_executed=0,
        candidate_sha256=sha256(candidate_bytes).hexdigest(),
        market=market,
        year=year,
        source_documents=documents,
        expected_days=len(expected_dates),
        supplied_days=len(days),
        blockers=tuple(sorted(set(blockers))),
    )
