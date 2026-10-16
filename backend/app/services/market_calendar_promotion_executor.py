"""Guarded persistence boundary for reviewed market-calendar candidates."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_calendar_day import MarketCalendarDay
from app.services.market_calendar_promotion_plan import (
    MarketCalendarPromotionPlan,
    build_market_calendar_promotion_plan,
)


_LOCK_NAMESPACE = "sgi-v2:market-calendar-promotion"
_CERTIFIED_SOURCE = "OFFICIAL_REVIEWED_ANNUAL_RULE"


class MarketCalendarPromotionExecutionError(RuntimeError):
    """A reviewed candidate cannot safely be persisted."""


@dataclass(frozen=True)
class MarketCalendarPromotionPreflight:
    schema_version: str
    dry_run: bool
    database_writes_executed: int
    plan: MarketCalendarPromotionPlan
    schema_ready: bool
    schema_blockers: tuple[str, ...]
    existing_count: int
    insert_count: int
    unchanged_count: int
    conflicts: tuple[dict[str, object], ...]

    @property
    def promotable(self) -> bool:
        return (
            self.plan.promotable
            and self.schema_ready
            and not self.schema_blockers
            and not self.conflicts
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["plan"] = self.plan.to_dict()
        payload["conflicts"] = list(self.conflicts)
        payload["promotable"] = self.promotable
        return payload


@dataclass(frozen=True)
class MarketCalendarPromotionExecutionResult:
    schema_version: str
    dry_run: bool
    database_writes_executed: int
    candidate_sha256: str
    inserted_count: int
    unchanged_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _lock_key(market: str, year: int) -> int:
    material = f"{_LOCK_NAMESPACE}:{market}:{year}".encode()
    unsigned = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return unsigned if unsigned < 2**63 else unsigned - 2**64


async def _acquire_promotion_lock(
    session: AsyncSession,
    *,
    market: str,
    year: int,
) -> None:
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _lock_key(market, year)},
        )


def _candidate_days(candidate: dict[str, object]) -> dict[date, dict[str, object]]:
    return {
        date.fromisoformat(str(raw["date"])): raw
        for raw in candidate["days"]  # validated by the planner before use
        if isinstance(raw, dict)
    }


async def _calendar_schema_ready(session: AsyncSession) -> bool:
    """Check the target table without relying on exception text from a query."""
    if session.get_bind().dialect.name != "postgresql":
        return True
    result = await session.execute(
        text("SELECT to_regclass('public.market_calendar_days')")
    )
    return result.scalar_one_or_none() is not None


async def _prepare_market_calendar_promotion(
    session: AsyncSession,
    *,
    candidate: dict[str, object],
    for_update: bool,
) -> MarketCalendarPromotionPreflight:
    plan = build_market_calendar_promotion_plan(candidate)
    if not plan.promotable:
        return MarketCalendarPromotionPreflight(
            schema_version="market-calendar-promotion-preflight.v1",
            dry_run=True,
            database_writes_executed=0,
            plan=plan,
            schema_ready=True,
            schema_blockers=(),
            existing_count=0,
            insert_count=0,
            unchanged_count=0,
            conflicts=(),
        )

    schema_ready = await _calendar_schema_ready(session)
    if not schema_ready:
        return MarketCalendarPromotionPreflight(
            schema_version="market-calendar-promotion-preflight.v1",
            dry_run=True,
            database_writes_executed=0,
            plan=plan,
            schema_ready=False,
            schema_blockers=("market_calendar_schema_not_ready",),
            existing_count=0,
            insert_count=0,
            unchanged_count=0,
            conflicts=(),
        )

    candidate_days = _candidate_days(candidate)
    statement = select(MarketCalendarDay).where(
        MarketCalendarDay.market == plan.market,
        MarketCalendarDay.calendar_date >= date(plan.year, 1, 1),
        MarketCalendarDay.calendar_date < date(plan.year + 1, 1, 1),
    )
    if for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    existing = {row.calendar_date: row for row in result.scalars().all()}

    conflicts: list[dict[str, object]] = []
    unchanged_count = 0
    for calendar_date, candidate_day in candidate_days.items():
        current = existing.get(calendar_date)
        if current is None:
            continue
        if (
            current.is_business_day == candidate_day["is_business_day"]
            and current.source == _CERTIFIED_SOURCE
            and current.source_reference == candidate_day["source_reference"]
        ):
            unchanged_count += 1
            continue
        conflicts.append(
            {
                "date": calendar_date.isoformat(),
                "persisted_is_business_day": current.is_business_day,
                "candidate_is_business_day": candidate_day["is_business_day"],
                "persisted_source": current.source,
                "candidate_source": _CERTIFIED_SOURCE,
                "persisted_source_reference": current.source_reference,
                "candidate_source_reference": candidate_day["source_reference"],
            }
        )

    return MarketCalendarPromotionPreflight(
        schema_version="market-calendar-promotion-preflight.v1",
        dry_run=True,
        database_writes_executed=0,
        plan=plan,
        schema_ready=True,
        schema_blockers=(),
        existing_count=len(existing),
        insert_count=len(candidate_days) - unchanged_count - len(conflicts),
        unchanged_count=unchanged_count,
        conflicts=tuple(conflicts),
    )


async def prepare_market_calendar_promotion(
    session: AsyncSession,
    *,
    candidate: dict[str, object],
) -> MarketCalendarPromotionPreflight:
    """Read persisted facts and build a no-write promotion preflight."""
    return await _prepare_market_calendar_promotion(
        session,
        candidate=candidate,
        for_update=False,
    )


async def execute_market_calendar_promotion(
    session: AsyncSession,
    *,
    candidate: dict[str, object],
    confirmation: str,
) -> MarketCalendarPromotionExecutionResult:
    """Insert only absent facts after exact candidate confirmation.

    The caller owns commit/rollback. Persisted facts are never updated: a
    mismatch remains a fail-closed conflict for an explicit correction flow.
    """
    plan = build_market_calendar_promotion_plan(candidate)
    if confirmation != plan.candidate_sha256:
        raise MarketCalendarPromotionExecutionError(
            "confirmation does not match the reviewed candidate"
        )
    if not plan.promotable or not plan.dry_run:
        raise MarketCalendarPromotionExecutionError(
            "executor accepts only a promotable dry-run candidate"
        )

    await _acquire_promotion_lock(
        session,
        market=plan.market,
        year=plan.year,
    )
    preflight = await _prepare_market_calendar_promotion(
        session,
        candidate=candidate,
        for_update=True,
    )
    if not preflight.promotable:
        raise MarketCalendarPromotionExecutionError(
            "persisted calendar facts conflict with the reviewed candidate"
        )

    candidate_days = _candidate_days(candidate)
    existing_dates = set()
    if preflight.unchanged_count:
        result = await session.execute(
            select(MarketCalendarDay.calendar_date).where(
                MarketCalendarDay.market == plan.market,
                MarketCalendarDay.calendar_date >= date(plan.year, 1, 1),
                MarketCalendarDay.calendar_date < date(plan.year + 1, 1, 1),
            )
        )
        existing_dates = set(result.scalars().all())
    inserts = [
        MarketCalendarDay(
            market=plan.market,
            calendar_date=calendar_date,
            is_business_day=bool(candidate_day["is_business_day"]),
            source=_CERTIFIED_SOURCE,
            source_reference=str(candidate_day["source_reference"]),
        )
        for calendar_date, candidate_day in candidate_days.items()
        if calendar_date not in existing_dates
    ]
    if inserts:
        session.add_all(inserts)
        await session.flush()
    return MarketCalendarPromotionExecutionResult(
        schema_version="market-calendar-promotion-execution.v1",
        dry_run=False,
        database_writes_executed=len(inserts),
        candidate_sha256=plan.candidate_sha256,
        inserted_count=len(inserts),
        unchanged_count=preflight.unchanged_count,
    )
