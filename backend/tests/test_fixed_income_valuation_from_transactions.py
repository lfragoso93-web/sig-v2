from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import (
    IncompleteBenchmarkCoverageError,
    get_fixed_income_totals_with_coverage_fallback,
    get_fixed_income_totals_from_transactions,
)
from app.services import fixed_income_valuation_service as service
from app.services.benchmark_rate_service import BenchmarkCoverageStatus


class _NoExecuteSession:
    async def execute(self, *_args, **_kwargs):
        raise AssertionError("preloaded fixed-income transactions should not be reloaded")


@pytest.mark.asyncio
async def test_fixed_income_totals_from_transactions_reuses_preloaded_rows():
    transactions = [
        Transaction(
            id=1,
            portfolio_id=7,
            ticker="CDB-TESTE",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: PREFIXADO | Taxa: 12%",
        )
    ]

    totals = await get_fixed_income_totals_from_transactions(
        _NoExecuteSession(),
        transactions,
        date(2026, 1, 12),
    )

    assert totals["invested_amount"] == Decimal("1000.00")
    assert totals["current_value"] > Decimal("1000.00")
    assert totals["income_amount"] > Decimal("0.00")


@pytest.mark.asyncio
async def test_fixed_income_totals_uses_latest_covered_benchmark_date(monkeypatch):
    calls = []

    async def fake_valuations(_db, _portfolio_id, target_date=None):
        calls.append(target_date)
        if len(calls) == 1:
            raise IncompleteBenchmarkCoverageError(
                "CDI",
                date(2026, 1, 2),
                date(2026, 9, 11),
                BenchmarkCoverageStatus.ABSENT,
            )
        return [
            service.FixedIncomeValuation(
                key=service.FixedIncomeKey(
                    name="LIG LIQUIDEZ",
                    indexer="CDI",
                    rate_pct=Decimal("100.0000"),
                    maturity=None,
                ),
                invested_amount=Decimal("121.14"),
                current_value=Decimal("122.48"),
                income_amount=Decimal("1.34"),
                income_pct=Decimal("1.1062"),
                applications_count=1,
            )
        ]

    monkeypatch.setattr(service, "get_fixed_income_valuations", fake_valuations)
    monkeypatch.setattr(
        service,
        "latest_covered_rate_date",
        AsyncMock(return_value=date(2026, 9, 10)),
    )

    totals, effective_date = await get_fixed_income_totals_with_coverage_fallback(
        object(),
        15,
        date(2026, 9, 11),
    )

    assert calls == [date(2026, 9, 11), date(2026, 9, 10)]
    assert effective_date == date(2026, 9, 10)
    assert totals["current_value"] == Decimal("122.48")


@pytest.mark.asyncio
async def test_new_cdi_application_without_next_rate_keeps_principal(monkeypatch):
    transactions = [
        Transaction(
            id=2,
            portfolio_id=7,
            ticker="LIG LIQUIDEZ",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("121.14"),
            fees=Decimal("0"),
            date=date(2026, 9, 10),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        )
    ]
    monkeypatch.setattr(
        service,
        "benchmark_coverage_status",
        AsyncMock(return_value=BenchmarkCoverageStatus.ABSENT),
    )
    monkeypatch.setattr(
        service,
        "latest_covered_rate_date",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        service,
        "benchmark_factor",
        AsyncMock(return_value=Decimal("1")),
    )

    totals = await get_fixed_income_totals_from_transactions(
        object(),
        transactions,
        date(2026, 9, 11),
    )

    assert totals["invested_amount"] == Decimal("121.14")
    assert totals["current_value"] == Decimal("121.14")
    assert totals["income_amount"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_fixed_income_uses_observed_factor_when_coverage_metadata_is_missing(monkeypatch):
    transactions = [
        Transaction(
            id=3,
            portfolio_id=7,
            ticker="CDB PORQUINHO OBJETIVO",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("7547.98"),
            fees=Decimal("0"),
            date=date(2026, 4, 14),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        )
    ]
    monkeypatch.setattr(
        service,
        "benchmark_coverage_status",
        AsyncMock(return_value=BenchmarkCoverageStatus.ABSENT),
    )
    monkeypatch.setattr(
        service,
        "latest_covered_rate_date",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        service,
        "benchmark_factor",
        AsyncMock(return_value=Decimal("1.0125")),
    )

    totals = await get_fixed_income_totals_from_transactions(
        object(),
        transactions,
        date(2026, 9, 11),
    )

    assert totals["invested_amount"] == Decimal("7547.98")
    assert totals["current_value"] == Decimal("7642.33")
    assert totals["income_amount"] == Decimal("94.35")
