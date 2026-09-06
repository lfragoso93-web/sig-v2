from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.services import fixed_income_valuation_service as valuation
from app.services.benchmark_rate_service import BenchmarkCoverageStatus


def _key(indexer: str, rate: str = "100") -> valuation.FixedIncomeKey:
    return valuation.FixedIncomeKey(
        name="CERT303-CDB-SYN-CDI-2028",
        indexer=indexer,
        rate_pct=Decimal(rate),
        maturity=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [BenchmarkCoverageStatus.ABSENT, BenchmarkCoverageStatus.PARTIAL],
)
async def test_cdi_fails_closed_without_complete_coverage(monkeypatch, status) -> None:
    coverage = AsyncMock(return_value=status)
    factor = AsyncMock(return_value=Decimal("1.01"))
    fallback = AsyncMock(return_value=Decimal("1.99"))
    monkeypatch.setattr(valuation, "benchmark_coverage_status", coverage)
    monkeypatch.setattr(valuation, "benchmark_factor", factor)
    monkeypatch.setattr(valuation, "_fallback_factor", fallback)

    with pytest.raises(valuation.IncompleteBenchmarkCoverageError) as excinfo:
        await valuation._application_factor(
            AsyncMock(),
            _key("CDI"),
            date(2026, 1, 8),
            date(2026, 2, 28),
        )

    assert excinfo.value.status is status
    factor.assert_not_awaited()
    fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_cdi_uses_persisted_factor_without_fallback(monkeypatch) -> None:
    coverage = AsyncMock(return_value=BenchmarkCoverageStatus.COMPLETE)
    factor = AsyncMock(return_value=Decimal("1.01"))
    fallback = AsyncMock(return_value=Decimal("1.99"))
    monkeypatch.setattr(valuation, "benchmark_coverage_status", coverage)
    monkeypatch.setattr(valuation, "benchmark_factor", factor)
    monkeypatch.setattr(valuation, "_fallback_factor", fallback)

    result = await valuation._application_factor(
        AsyncMock(),
        _key("CDI"),
        date(2026, 1, 8),
        date(2026, 2, 28),
    )

    assert result == Decimal("1.01")
    factor.assert_awaited_once()
    fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_selic_uses_same_strict_coverage_contract(monkeypatch) -> None:
    coverage = AsyncMock(return_value=BenchmarkCoverageStatus.ABSENT)
    monkeypatch.setattr(valuation, "benchmark_coverage_status", coverage)

    with pytest.raises(valuation.IncompleteBenchmarkCoverageError) as excinfo:
        await valuation._application_factor(
            AsyncMock(),
            _key("SELIC"),
            date(2026, 1, 8),
            date(2026, 2, 28),
        )

    assert excinfo.value.indicator == "SELIC"


@pytest.mark.asyncio
async def test_prefixado_preserves_contractual_annual_compounding(monkeypatch) -> None:
    coverage = AsyncMock(return_value=BenchmarkCoverageStatus.ABSENT)
    fallback = AsyncMock(return_value=Decimal("1.02"))
    monkeypatch.setattr(valuation, "benchmark_coverage_status", coverage)
    monkeypatch.setattr(valuation, "_fallback_factor", fallback)

    result = await valuation._application_factor(
        AsyncMock(),
        _key("PREFIXADO", "12"),
        date(2026, 1, 8),
        date(2026, 2, 28),
    )

    assert result == Decimal("1.02")
    coverage.assert_not_awaited()
    fallback.assert_awaited_once()
