"""Testes do scanner read-only de comparação fiscal em lote."""

from datetime import date
from types import SimpleNamespace

import pytest
from app.services.irpf_comparison_batch_service import (
    FiscalComparisonTarget,
    build_batch_report,
    compare_discovered_targets,
    discover_comparison_targets,
)
from app.services.irpf_legacy_comparison_service import (
    FiscalAnnualComparison,
    FiscalComparisonKind,
    FiscalMonthlyComparison,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup


def _comparison(
    portfolio_id: int,
    year: int,
    *,
    divergent: bool,
) -> FiscalAnnualComparison:
    kinds = (
        (FiscalComparisonKind.CLASS_SEGREGATION,)
        if divergent
        else (FiscalComparisonKind.MATCH,)
    )
    return FiscalAnnualComparison(
        portfolio_id=portfolio_id,
        year=year,
        monthly=(
            FiscalMonthlyComparison(
                competence_month=f"{year}-01",
                canonical_realized_pnl_brl=0,
                legacy_realized_pnl_brl=0,
                canonical_taxable_base_brl=0,
                legacy_taxable_base_brl=0,
                canonical_tax_due_brl=0,
                legacy_tax_due_brl=0,
                kinds=kinds,
                canonical_groups=(TaxAssessmentGroup.STOCKS,),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_discover_targets_groups_sales_by_portfolio_and_year() -> None:
    db = SimpleNamespace()

    class Result:
        def all(self):
            return [
                (2, 2024, 3, date(2024, 5, 1)),
                (1, 2023, 1, date(2023, 2, 1)),
                (1, 2023, 2, date(2023, 8, 1)),
            ]

    async def execute(statement):
        return Result()

    db.execute = execute
    result = await discover_comparison_targets(db)

    assert result == (
        FiscalComparisonTarget(1, 2023, 2, date(2023, 2, 1), date(2023, 8, 1)),
        FiscalComparisonTarget(2, 2024, 1, date(2024, 5, 1), date(2024, 5, 1)),
    )


@pytest.mark.parametrize(
    ("start_year", "end_year", "message"),
    [
        (1899, None, "start_year inválido"),
        (None, 10000, "end_year inválido"),
        (2025, 2024, "end_year deve ser igual ou posterior a start_year"),
    ],
)
@pytest.mark.asyncio
async def test_discover_targets_rejects_invalid_ranges(
    start_year,
    end_year,
    message,
) -> None:
    with pytest.raises(ValueError, match=message):
        await discover_comparison_targets(
            SimpleNamespace(),
            start_year=start_year,
            end_year=end_year,
        )


def test_batch_report_aggregates_matches_and_divergences() -> None:
    targets = [
        FiscalComparisonTarget(2, 2024, 1, date(2024, 1, 1), date(2024, 1, 1)),
        FiscalComparisonTarget(1, 2023, 1, date(2023, 1, 1), date(2023, 1, 1)),
    ]
    report = build_batch_report(
        targets=targets,
        comparisons=[
            _comparison(2, 2024, divergent=True),
            _comparison(1, 2023, divergent=False),
        ],
    )

    assert [(item.portfolio_id, item.year) for item in report.targets] == [
        (1, 2023),
        (2, 2024),
    ]
    assert report.months_compared == 2
    assert report.matching_months == 1
    assert report.divergent_months == 1
    assert report.divergence_counts == {
        FiscalComparisonKind.CLASS_SEGREGATION: 1,
    }


@pytest.mark.asyncio
async def test_compare_discovered_targets_executes_each_target(monkeypatch) -> None:
    targets = (
        FiscalComparisonTarget(1, 2023, 1, date(2023, 1, 1), date(2023, 1, 1)),
        FiscalComparisonTarget(2, 2024, 1, date(2024, 1, 1), date(2024, 1, 1)),
    )
    calls = []

    async def fake_discover(db, *, start_year, end_year):
        assert start_year == 2023
        assert end_year == 2024
        return targets

    async def fake_compare(db, portfolio_id, year):
        calls.append((portfolio_id, year))
        return _comparison(portfolio_id, year, divergent=portfolio_id == 2)

    monkeypatch.setattr(
        "app.services.irpf_comparison_batch_service.discover_comparison_targets",
        fake_discover,
    )
    monkeypatch.setattr(
        "app.services.irpf_comparison_batch_service.compare_annual_common_with_legacy",
        fake_compare,
    )

    report = await compare_discovered_targets(
        SimpleNamespace(),
        start_year=2023,
        end_year=2024,
    )

    assert calls == [(1, 2023), (2, 2024)]
    assert report.months_compared == 2
    assert report.divergent_months == 1
