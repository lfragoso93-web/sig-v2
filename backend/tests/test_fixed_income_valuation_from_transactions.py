from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import (
    IncompleteBenchmarkCoverageError,
    fixed_income_coverage_from_transactions,
    get_fixed_income_totals_with_coverage_fallback,
    get_fixed_income_totals_from_transactions,
    get_fixed_income_valuations_from_transactions,
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


@pytest.mark.asyncio
async def test_fixed_income_partial_coverage_does_not_zero_whole_group(monkeypatch):
    transactions = [
        Transaction(
            id=4,
            portfolio_id=7,
            ticker="CDB PORQUINHO OBJETIVO",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000.00"),
            fees=Decimal("0"),
            date=date(2026, 8, 5),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
        Transaction(
            id=5,
            portfolio_id=7,
            ticker="CDB PORQUINHO OBJETIVO",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("200.00"),
            fees=Decimal("0"),
            date=date(2026, 9, 4),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
    ]

    async def fake_coverage(_db, _indicator, start, _target, **_kwargs):
        if start == date(2026, 8, 5):
            return BenchmarkCoverageStatus.PARTIAL
        return BenchmarkCoverageStatus.PARTIAL

    async def fake_latest(_db, _indicator, start, _target, **_kwargs):
        if start == date(2026, 8, 5):
            return date(2026, 9, 4)
        return date(2026, 9, 4)

    async def fake_factor(_db, _indicator, start, _target, **_kwargs):
        if start == date(2026, 8, 5):
            return Decimal("1.0100")
        return Decimal("1")

    monkeypatch.setattr(service, "benchmark_coverage_status", fake_coverage)
    monkeypatch.setattr(service, "latest_covered_rate_date", fake_latest)
    monkeypatch.setattr(service, "benchmark_factor", fake_factor)

    totals = await get_fixed_income_totals_from_transactions(
        object(),
        transactions,
        date(2026, 9, 11),
    )

    assert totals["invested_amount"] == Decimal("1200.00")
    assert totals["current_value"] == Decimal("1210.00")
    assert totals["income_amount"] == Decimal("10.00")


@pytest.mark.asyncio
async def test_open_applications_expose_worst_benchmark_coverage(monkeypatch):
    transactions = [
        Transaction(
            id=6,
            portfolio_id=7,
            ticker="CDB-CDI",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
        Transaction(
            id=7,
            portfolio_id=7,
            ticker="CDB-PRE",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("500"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: PREFIXADO | Taxa: 12%",
        ),
    ]
    coverage = AsyncMock(return_value=BenchmarkCoverageStatus.PARTIAL)
    monkeypatch.setattr(service, "benchmark_coverage_status", coverage)

    result = await fixed_income_coverage_from_transactions(
        object(),
        transactions,
        date(2026, 1, 10),
    )

    assert result is BenchmarkCoverageStatus.PARTIAL
    coverage.assert_awaited_once()


@pytest.mark.asyncio
async def test_fully_redeemed_application_does_not_block_coverage(monkeypatch):
    transactions = [
        Transaction(
            id=8,
            portfolio_id=7,
            ticker="CDB-CDI",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
        Transaction(
            id=9,
            portfolio_id=7,
            ticker="CDB-CDI",
            asset_type="RENDA_FIXA",
            operation=OperationType.sell,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 5),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
    ]
    coverage = AsyncMock(return_value=BenchmarkCoverageStatus.ABSENT)
    monkeypatch.setattr(service, "benchmark_coverage_status", coverage)

    result = await fixed_income_coverage_from_transactions(
        object(),
        transactions,
        date(2026, 1, 10),
    )

    assert result is BenchmarkCoverageStatus.COMPLETE
    coverage.assert_not_awaited()


@pytest.mark.asyncio
async def test_partial_redemption_preserves_fifo_applications_and_start_dates(
    monkeypatch,
):
    transactions = [
        Transaction(
            id=10,
            portfolio_id=7,
            ticker="CDB-FIFO",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
        Transaction(
            id=11,
            portfolio_id=7,
            ticker="CDB-FIFO",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("500"),
            fees=Decimal("0"),
            date=date(2026, 1, 5),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
        Transaction(
            id=12,
            portfolio_id=7,
            ticker="CDB-FIFO",
            asset_type="RENDA_FIXA",
            operation=OperationType.sell,
            quantity=Decimal("1"),
            price=Decimal("600"),
            fees=Decimal("0"),
            date=date(2026, 1, 8),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
    ]

    async def factor(_db, _key, start, _target):
        return Decimal("1.10") if start == date(2026, 1, 2) else Decimal("1.04")

    monkeypatch.setattr(service, "_application_factor", factor)

    valuations = await get_fixed_income_valuations_from_transactions(
        object(), transactions, date(2026, 1, 10)
    )

    assert len(valuations) == 1
    assert valuations[0].applications_count == 2
    assert valuations[0].invested_amount == Decimal("900.00")
    assert valuations[0].current_value == Decimal("960.00")
    assert valuations[0].income_amount == Decimal("60.00")


@pytest.mark.asyncio
async def test_partial_redemption_only_consumes_matching_product_indexer(monkeypatch):
    transactions = [
        Transaction(
            id=13,
            portfolio_id=7,
            ticker="CDB-MULTI",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
        Transaction(
            id=14,
            portfolio_id=7,
            ticker="CDB-MULTI",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("700"),
            fees=Decimal("0"),
            date=date(2026, 1, 3),
            currency="BRL",
            notes="Indexador: PREFIXADO | Taxa: 12%",
        ),
        Transaction(
            id=15,
            portfolio_id=7,
            ticker="CDB-MULTI",
            asset_type="RENDA_FIXA",
            operation=OperationType.sell,
            quantity=Decimal("1"),
            price=Decimal("300"),
            fees=Decimal("0"),
            date=date(2026, 1, 8),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 100%",
        ),
    ]
    monkeypatch.setattr(
        service,
        "_application_factor",
        AsyncMock(return_value=Decimal("1")),
    )

    valuations = await get_fixed_income_valuations_from_transactions(
        object(), transactions, date(2026, 1, 10)
    )
    by_indexer = {valuation.key.indexer: valuation for valuation in valuations}

    assert by_indexer["CDI"].invested_amount == Decimal("700.00")
    assert by_indexer["PREFIXADO"].invested_amount == Decimal("700.00")
    assert by_indexer["CDI"].applications_count == 1
    assert by_indexer["PREFIXADO"].applications_count == 1
