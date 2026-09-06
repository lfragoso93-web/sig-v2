"""Synthetic benchmark-rate seed for certification issue #323/#303."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.rate_history import RateHistory
from app.models.rate_history_coverage import RateHistoryCoverage

SYNTHETIC_BENCHMARK_SOURCE = "synthetic-certification"
SYNTHETIC_BENCHMARK_INDICATOR = "CDI"


@dataclass(frozen=True)
class SyntheticBenchmarkRateSeedResult:
    rates_created: int
    rates_reused: int
    coverages_created: int
    coverages_reused: int


@dataclass(frozen=True)
class SyntheticBenchmarkContract:
    indicator: str
    source: str
    coverage_start: date
    coverage_end: date
    observation_date: date
    rate_daily: Decimal


def _parse_date(raw: object, *, field: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError) as exc:
        raise SyntheticSeedContractError(
            f"synthetic benchmark {field} is invalid"
        ) from exc


def _parse_decimal(raw: object, *, field: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SyntheticSeedContractError(
            f"synthetic benchmark {field} is invalid"
        ) from exc
    if not value.is_finite():
        raise SyntheticSeedContractError(
            f"synthetic benchmark {field} must be finite"
        )
    return value


def _expected_contract(fixture: dict) -> SyntheticBenchmarkContract:
    raw = fixture.get("benchmark_rates")
    if not isinstance(raw, dict):
        raise SyntheticSeedContractError("synthetic benchmark contract is missing")

    indicator = str(raw.get("indicator") or "").upper().strip()
    source = str(raw.get("source") or "").strip()
    if indicator != SYNTHETIC_BENCHMARK_INDICATOR:
        raise SyntheticSeedContractError("synthetic benchmark indicator must be CDI")
    if source != SYNTHETIC_BENCHMARK_SOURCE:
        raise SyntheticSeedContractError("synthetic benchmark source is invalid")

    coverage_start = _parse_date(raw.get("coverage_start"), field="coverage_start")
    coverage_end = _parse_date(raw.get("coverage_end"), field="coverage_end")
    if coverage_end <= coverage_start:
        raise SyntheticSeedContractError("synthetic benchmark coverage range is invalid")

    observations = raw.get("observations")
    if not isinstance(observations, list) or len(observations) != 1:
        raise SyntheticSeedContractError(
            "synthetic benchmark must contain exactly one deterministic observation"
        )
    observation = observations[0]
    if not isinstance(observation, dict):
        raise SyntheticSeedContractError("synthetic benchmark observation is invalid")

    observation_date = _parse_date(observation.get("date"), field="observation date")
    rate_daily = _parse_decimal(observation.get("rate_daily"), field="rate_daily")
    if observation_date != coverage_end:
        raise SyntheticSeedContractError(
            "synthetic benchmark observation must be anchored at coverage_end"
        )
    if rate_daily != Decimal("1.00000000"):
        raise SyntheticSeedContractError(
            "synthetic benchmark daily rate must produce the certified 1.01 factor"
        )

    fixed_income_txs = [
        tx
        for tx in fixture.get("transactions", [])
        if isinstance(tx, dict) and tx.get("asset_type") == "RENDA_FIXA"
    ]
    if len(fixed_income_txs) != 1:
        raise SyntheticSeedContractError(
            "synthetic benchmark requires exactly one RENDA_FIXA transaction"
        )
    tx = fixed_income_txs[0]
    if _parse_date(tx.get("date"), field="RENDA_FIXA transaction date") != coverage_start:
        raise SyntheticSeedContractError(
            "synthetic benchmark coverage_start must match RENDA_FIXA transaction date"
        )
    notes = str(tx.get("notes") or "")
    if f"Benchmark Source: {source}" not in notes:
        raise SyntheticSeedContractError(
            "synthetic RENDA_FIXA transaction must declare benchmark source"
        )

    market_prices = fixture.get("market_prices")
    if not isinstance(market_prices, dict):
        raise SyntheticSeedContractError("synthetic market price contract is invalid")
    if _parse_date(market_prices.get("as_of"), field="market as_of") != coverage_end:
        raise SyntheticSeedContractError(
            "synthetic benchmark coverage_end must match market as_of"
        )

    return SyntheticBenchmarkContract(
        indicator=indicator,
        source=source,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        observation_date=observation_date,
        rate_daily=rate_daily,
    )


def _is_canonical_rate(row: RateHistory, expected: SyntheticBenchmarkContract) -> bool:
    try:
        rate_daily = Decimal(str(row.rate_daily))
    except (InvalidOperation, TypeError, ValueError):
        return False

    return (
        row.indicator == expected.indicator
        and row.date == expected.observation_date
        and rate_daily == expected.rate_daily
        and row.rate_monthly is None
        and row.rate_annual is None
        and row.source == expected.source
    )


def _is_canonical_coverage(
    row: RateHistoryCoverage,
    expected: SyntheticBenchmarkContract,
) -> bool:
    return (
        row.indicator == expected.indicator
        and row.start_date == expected.coverage_start
        and row.end_date == expected.coverage_end
        and row.source == expected.source
    )


async def seed_synthetic_benchmark_rate(
    db: AsyncSession,
) -> SyntheticBenchmarkRateSeedResult:
    """Seed isolated CDI source data and proven coverage for CERT303 Renda Fixa."""
    fixture = load_portfolio_synthetic_certification_fixture()
    expected = _expected_contract(fixture)

    source_rows_result = await db.execute(
        select(RateHistory).where(
            RateHistory.indicator == expected.indicator,
            RateHistory.source == expected.source,
            RateHistory.date >= expected.coverage_start,
            RateHistory.date <= expected.coverage_end,
        )
    )
    source_rows = list(source_rows_result.scalars().all())
    if source_rows:
        if len(source_rows) != 1 or not _is_canonical_rate(source_rows[0], expected):
            raise SyntheticSeedContractError(
                "synthetic benchmark collision; source-qualified CDI rows are not canonical"
            )
        rates_created = 0
        rates_reused = 1
    else:
        identity_result = await db.execute(
            select(RateHistory).where(
                RateHistory.indicator == expected.indicator,
                RateHistory.date == expected.observation_date,
            )
        )
        identity_rows = list(identity_result.scalars().all())
        if identity_rows:
            raise SyntheticSeedContractError(
                "synthetic benchmark collision at CDI observation date"
            )
        db.add(
            RateHistory(
                indicator=expected.indicator,
                date=expected.observation_date,
                rate_daily=expected.rate_daily,
                rate_monthly=None,
                rate_annual=None,
                source=expected.source,
            )
        )
        rates_created = 1
        rates_reused = 0

    coverage_result = await db.execute(
        select(RateHistoryCoverage).where(
            RateHistoryCoverage.indicator == expected.indicator,
            RateHistoryCoverage.source == expected.source,
            RateHistoryCoverage.start_date <= expected.coverage_end,
            RateHistoryCoverage.end_date >= expected.coverage_start,
        )
    )
    coverages = list(coverage_result.scalars().all())
    if coverages:
        if len(coverages) != 1 or not _is_canonical_coverage(coverages[0], expected):
            raise SyntheticSeedContractError(
                "synthetic benchmark coverage collision; interval is not canonical"
            )
        coverages_created = 0
        coverages_reused = 1
    else:
        db.add(
            RateHistoryCoverage(
                indicator=expected.indicator,
                start_date=expected.coverage_start,
                end_date=expected.coverage_end,
                source=expected.source,
            )
        )
        coverages_created = 1
        coverages_reused = 0

    if rates_created or coverages_created:
        await db.commit()

    return SyntheticBenchmarkRateSeedResult(
        rates_created=rates_created,
        rates_reused=rates_reused,
        coverages_created=coverages_created,
        coverages_reused=coverages_reused,
    )
