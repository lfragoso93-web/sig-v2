import json
from argparse import Namespace
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_calendar_day import MarketCalendarDay
from app.cli import promote_market_calendar as cli
from app.services.market_calendar_promotion_executor import (
    MarketCalendarPromotionExecutionError,
    execute_market_calendar_promotion,
    prepare_market_calendar_promotion,
)
from app.services.market_calendar_promotion_plan import (
    build_market_calendar_promotion_plan,
    build_treasury_standard_calendar_candidate,
)


def _reviewed_candidate() -> dict[str, object]:
    rule_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "market-calendar-tesouro-2026-rule.json"
    )
    rule = json.loads(rule_path.read_text(encoding="utf-8"))
    return build_treasury_standard_calendar_candidate(rule)


async def _count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(MarketCalendarDay.id)))
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_preflight_is_read_only_and_reports_all_absent_days(
    db: AsyncSession,
) -> None:
    preflight = await prepare_market_calendar_promotion(
        db,
        candidate=_reviewed_candidate(),
    )

    assert preflight.promotable is True
    assert preflight.dry_run is True
    assert preflight.database_writes_executed == 0
    assert preflight.insert_count == 365
    assert preflight.unchanged_count == 0
    assert await _count(db) == 0


@pytest.mark.asyncio
async def test_execute_requires_exact_candidate_confirmation(
    db: AsyncSession,
) -> None:
    with pytest.raises(MarketCalendarPromotionExecutionError, match="does not match"):
        await execute_market_calendar_promotion(
            db,
            candidate=_reviewed_candidate(),
            confirmation="not-the-reviewed-candidate",
        )

    assert await _count(db) == 0


@pytest.mark.asyncio
async def test_execute_inserts_absent_facts_and_is_idempotent(
    db: AsyncSession,
) -> None:
    candidate = _reviewed_candidate()
    plan = build_market_calendar_promotion_plan(candidate)

    result = await execute_market_calendar_promotion(
        db,
        candidate=candidate,
        confirmation=plan.candidate_sha256,
    )

    assert result.database_writes_executed == 365
    assert result.inserted_count == 365
    assert await _count(db) == 365

    repeated = await execute_market_calendar_promotion(
        db,
        candidate=candidate,
        confirmation=plan.candidate_sha256,
    )
    assert repeated.database_writes_executed == 0
    assert repeated.unchanged_count == 365


@pytest.mark.asyncio
async def test_conflicting_persisted_fact_blocks_execution(db: AsyncSession) -> None:
    candidate = _reviewed_candidate()
    db.add(
        MarketCalendarDay(
            market="TESOURO_DIRETO_STANDARD",
            calendar_date=date(2026, 1, 1),
            is_business_day=True,
            source="MANUAL",
            source_reference="manual://incorrect",
        )
    )
    await db.flush()

    preflight = await prepare_market_calendar_promotion(db, candidate=candidate)
    assert preflight.promotable is False
    assert preflight.insert_count == 364
    assert preflight.conflicts[0]["date"] == "2026-01-01"

    plan = build_market_calendar_promotion_plan(candidate)
    with pytest.raises(MarketCalendarPromotionExecutionError, match="conflict"):
        await execute_market_calendar_promotion(
            db,
            candidate=candidate,
            confirmation=plan.candidate_sha256,
        )
    assert await _count(db) == 1


@pytest.mark.asyncio
async def test_cli_rejects_execute_without_confirmation_before_database_access() -> None:
    with pytest.raises(ValueError, match="requires --confirmation"):
        await cli._main(
            Namespace(
                execute=True,
                confirmation=None,
                candidate_file=Path("not-read.json"),
            )
        )
