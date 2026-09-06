from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.benchmark_rate_service import (
    BenchmarkCoverageStatus,
    benchmark_coverage_status,
)


def _db_with_intervals(*intervals):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(intervals)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    return db


@pytest.mark.asyncio
async def test_coverage_is_absent_without_proven_intervals() -> None:
    db = _db_with_intervals()

    status = await benchmark_coverage_status(
        db,
        "CDI",
        date(2026, 1, 8),
        date(2026, 2, 28),
    )

    assert status is BenchmarkCoverageStatus.ABSENT


@pytest.mark.asyncio
async def test_coverage_is_partial_when_proven_ranges_have_calendar_gap() -> None:
    db = _db_with_intervals(
        SimpleNamespace(start_date=date(2026, 1, 8), end_date=date(2026, 1, 31)),
        SimpleNamespace(start_date=date(2026, 2, 2), end_date=date(2026, 2, 28)),
    )

    status = await benchmark_coverage_status(
        db,
        "CDI",
        date(2026, 1, 8),
        date(2026, 2, 28),
    )

    assert status is BenchmarkCoverageStatus.PARTIAL


@pytest.mark.asyncio
async def test_coverage_is_complete_when_adjacent_proven_ranges_cover_request() -> None:
    db = _db_with_intervals(
        SimpleNamespace(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31)),
        SimpleNamespace(start_date=date(2026, 2, 1), end_date=date(2026, 3, 10)),
    )

    status = await benchmark_coverage_status(
        db,
        "CDI",
        date(2026, 1, 8),
        date(2026, 2, 28),
    )

    assert status is BenchmarkCoverageStatus.COMPLETE


@pytest.mark.asyncio
async def test_zero_length_period_is_complete_without_database_lookup() -> None:
    db = _db_with_intervals()

    status = await benchmark_coverage_status(
        db,
        "SELIC",
        date(2026, 2, 28),
        date(2026, 2, 28),
    )

    assert status is BenchmarkCoverageStatus.COMPLETE
    db.execute.assert_not_awaited()
