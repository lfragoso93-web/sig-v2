from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.certification.portfolio_seed_benchmark_rate_service import (
    SYNTHETIC_BENCHMARK_SOURCE,
    seed_synthetic_benchmark_rate,
)
from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.models.rate_history import RateHistory
from app.models.rate_history_coverage import RateHistoryCoverage


def _result(*rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(rows)
    return result


def _db(*results):
    return SimpleNamespace(
        execute=AsyncMock(side_effect=list(results)),
        add=MagicMock(),
        commit=AsyncMock(),
    )


def _canonical_rate():
    return SimpleNamespace(
        indicator="CDI",
        date=date(2026, 2, 28),
        rate_daily=Decimal("1.00000000"),
        rate_monthly=None,
        rate_annual=None,
        source=SYNTHETIC_BENCHMARK_SOURCE,
    )


def _canonical_coverage():
    return SimpleNamespace(
        indicator="CDI",
        start_date=date(2026, 1, 11),
        end_date=date(2026, 2, 28),
        source=SYNTHETIC_BENCHMARK_SOURCE,
    )


@pytest.mark.asyncio
async def test_seed_creates_isolated_rate_and_coverage() -> None:
    db = _db(_result(), _result(), _result())

    result = await seed_synthetic_benchmark_rate(db)

    assert result.rates_created == 1
    assert result.rates_reused == 0
    assert result.coverages_created == 1
    assert result.coverages_reused == 0
    assert db.add.call_count == 2
    rate_row = db.add.call_args_list[0].args[0]
    coverage_row = db.add.call_args_list[1].args[0]
    assert isinstance(rate_row, RateHistory)
    assert rate_row.indicator == "CDI"
    assert rate_row.date == date(2026, 2, 28)
    assert rate_row.rate_daily == Decimal("1.00000000")
    assert rate_row.source == SYNTHETIC_BENCHMARK_SOURCE
    assert isinstance(coverage_row, RateHistoryCoverage)
    assert coverage_row.start_date == date(2026, 1, 11)
    assert coverage_row.end_date == date(2026, 2, 28)
    assert coverage_row.source == SYNTHETIC_BENCHMARK_SOURCE
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_reuses_exact_rate_and_coverage_without_write() -> None:
    db = _db(_result(_canonical_rate()), _result(_canonical_coverage()))

    result = await seed_synthetic_benchmark_rate(db)

    assert result.rates_created == 0
    assert result.rates_reused == 1
    assert result.coverages_created == 0
    assert result.coverages_reused == 1
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_when_observation_date_is_owned_by_other_source() -> None:
    foreign = SimpleNamespace(
        indicator="CDI",
        date=date(2026, 2, 28),
        rate_daily=Decimal("0.05"),
        rate_monthly=None,
        rate_annual=None,
        source="BCB_SGS",
    )
    db = _db(_result(), _result(foreign))

    with pytest.raises(SyntheticSeedContractError, match="observation date"):
        await seed_synthetic_benchmark_rate(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_extra_source_qualified_rate() -> None:
    extra = SimpleNamespace(
        indicator="CDI",
        date=date(2026, 2, 20),
        rate_daily=Decimal("0.50"),
        rate_monthly=None,
        rate_annual=None,
        source=SYNTHETIC_BENCHMARK_SOURCE,
    )
    db = _db(_result(extra))

    with pytest.raises(SyntheticSeedContractError, match="not canonical"):
        await seed_synthetic_benchmark_rate(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_noncanonical_coverage() -> None:
    wrong_coverage = SimpleNamespace(
        indicator="CDI",
        start_date=date(2026, 1, 12),
        end_date=date(2026, 2, 28),
        source=SYNTHETIC_BENCHMARK_SOURCE,
    )
    db = _db(_result(_canonical_rate()), _result(wrong_coverage))

    with pytest.raises(SyntheticSeedContractError, match="coverage collision"):
        await seed_synthetic_benchmark_rate(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()
