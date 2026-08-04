"""Testes da comparação read-only entre o motor canônico e o legado."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.irpf_annual_common_assessment_service import (
    FiscalAnnualCommonAssessment,
)
from app.services.irpf_common_loss_carryforward import (
    FiscalMonthlyLossCompensation,
)
from app.services.irpf_legacy_comparison_service import (
    FiscalComparisonKind,
    build_annual_comparison,
    compare_annual_common_with_legacy,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup


def _canonical(
    *,
    month: str,
    group: TaxAssessmentGroup,
    realized: int,
    taxable: int,
    tax: int,
    exemption: bool = False,
    loss_used: int = 0,
) -> FiscalMonthlyLossCompensation:
    return FiscalMonthlyLossCompensation(
        competence_month=month,
        group=group,
        realized_pnl_brl=Decimal(realized),
        exemption_applied=exemption,
        opening_loss_carryforward_brl=Decimal(0),
        loss_used_brl=Decimal(loss_used),
        closing_loss_carryforward_brl=Decimal(0),
        taxable_base_brl=Decimal(taxable),
        tax_rate=Decimal("0.15"),
        tax_due_brl=Decimal(tax),
    )


def _annual(*items: FiscalMonthlyLossCompensation) -> FiscalAnnualCommonAssessment:
    return FiscalAnnualCommonAssessment(
        portfolio_id=1,
        year=2024,
        start_date=SimpleNamespace(),
        end_date=SimpleNamespace(),
        monthly=items,
        total_realized_pnl_brl=Decimal(0),
        total_taxable_base_brl=Decimal(0),
        total_tax_due_brl=Decimal(0),
        closing_loss_carryforward_by_group={},
    )


def _legacy(month: str, realized: int, taxable: int, tax: int):
    return SimpleNamespace(
        mes=month,
        lucro_swing_trade=float(realized),
        base_calculo=float(taxable),
        ir_devido_swing=float(tax),
    )


def test_simple_stock_month_matches_legacy() -> None:
    result = build_annual_comparison(
        portfolio_id=1,
        year=2024,
        canonical=_annual(
            _canonical(
                month="2024-01",
                group=TaxAssessmentGroup.STOCKS,
                realized=1000,
                taxable=1000,
                tax=150,
            )
        ),
        legacy_months=[_legacy("2024-01", 1000, 1000, 150)],
    )

    assert result.has_divergences is False
    assert result.monthly[0].kinds == (FiscalComparisonKind.MATCH,)


@pytest.mark.parametrize(
    "group",
    [
        TaxAssessmentGroup.BDR,
        TaxAssessmentGroup.ETF,
        TaxAssessmentGroup.REAL_ESTATE_FUNDS,
    ],
)
def test_non_stock_group_divergence_is_classified(group) -> None:
    result = build_annual_comparison(
        portfolio_id=1,
        year=2024,
        canonical=_annual(
            _canonical(
                month="2024-02",
                group=group,
                realized=500,
                taxable=500,
                tax=75,
            )
        ),
        legacy_months=[_legacy("2024-02", 500, 0, 0)],
    )

    assert FiscalComparisonKind.CLASS_SEGREGATION in result.monthly[0].kinds


def test_stock_exemption_divergence_is_classified() -> None:
    result = build_annual_comparison(
        portfolio_id=1,
        year=2024,
        canonical=_annual(
            _canonical(
                month="2024-03",
                group=TaxAssessmentGroup.STOCKS,
                realized=800,
                taxable=0,
                tax=0,
                exemption=True,
            )
        ),
        legacy_months=[_legacy("2024-03", 800, 100, 15)],
    )

    assert FiscalComparisonKind.STOCK_EXEMPTION in result.monthly[0].kinds


def test_loss_carryforward_divergence_is_classified() -> None:
    result = build_annual_comparison(
        portfolio_id=1,
        year=2024,
        canonical=_annual(
            _canonical(
                month="2024-04",
                group=TaxAssessmentGroup.STOCKS,
                realized=1000,
                taxable=400,
                tax=60,
                loss_used=600,
            )
        ),
        legacy_months=[_legacy("2024-04", 1000, 1000, 150)],
    )

    assert FiscalComparisonKind.LOSS_CARRYFORWARD in result.monthly[0].kinds


def test_missing_months_are_reported_on_both_sides() -> None:
    result = build_annual_comparison(
        portfolio_id=1,
        year=2024,
        canonical=_annual(
            _canonical(
                month="2024-05",
                group=TaxAssessmentGroup.STOCKS,
                realized=100,
                taxable=100,
                tax=15,
            )
        ),
        legacy_months=[_legacy("2024-06", 200, 200, 30)],
    )

    assert result.monthly[0].kinds[0] is FiscalComparisonKind.LEGACY_MISSING_MONTH
    assert result.monthly[1].kinds[0] is FiscalComparisonKind.CANONICAL_MISSING_MONTH


@pytest.mark.asyncio
async def test_async_comparator_executes_both_engines(monkeypatch) -> None:
    canonical = _annual()
    legacy = [_legacy("2024-07", 0, 0, 0)]
    calls = []

    async def fake_canonical(db, portfolio_id, year):
        calls.append(("canonical", db, portfolio_id, year))
        return canonical

    async def fake_legacy(db, portfolio_id, year):
        calls.append(("legacy", db, portfolio_id, year))
        return legacy

    monkeypatch.setattr(
        "app.services.irpf_legacy_comparison_service.assess_annual_common_operations",
        fake_canonical,
    )
    monkeypatch.setattr(
        "app.services.irpf_legacy_comparison_service.calc_ganhos_capital",
        fake_legacy,
    )
    db = SimpleNamespace()

    result = await compare_annual_common_with_legacy(db, 9, 2024)

    assert calls == [
        ("canonical", db, 9, 2024),
        ("legacy", db, 9, 2024),
    ]
    assert result.portfolio_id == 9
    assert result.year == 2024
