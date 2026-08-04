"""Testes do comparador mensal integrado entre canônico e legado."""

from decimal import Decimal
from types import SimpleNamespace

from app.services.irpf_integrated_legacy_comparison import (
    IntegratedFiscalComparisonKind,
    build_integrated_annual_comparison,
)


def _canonical(*, swing=None, day_trade=None):
    return SimpleNamespace(
        swing=SimpleNamespace(monthly=tuple(swing or ())),
        day_trade_monthly=tuple(day_trade or ()),
    )


def test_integrated_comparison_marks_equivalent_month_as_match() -> None:
    canonical = _canonical(
        swing=(
            SimpleNamespace(
                competence_month="2024-05",
                realized_pnl_brl=Decimal(100),
                taxable_base_brl=Decimal(100),
                tax_due_brl=Decimal(15),
                loss_used_brl=Decimal(0),
            ),
        ),
        day_trade=(
            SimpleNamespace(
                competence_month="2024-05",
                realized_pnl_brl=Decimal(50),
                taxable_base_brl=Decimal(50),
                tax_due_brl=Decimal(10),
                loss_used_brl=Decimal(0),
            ),
        ),
    )
    legacy = [
        SimpleNamespace(
            mes="2024-05",
            lucro_swing_trade=100,
            base_calculo=100,
            ir_devido_swing=15,
            lucro_day_trade=50,
            ir_devido_day_trade=10,
        )
    ]

    result = build_integrated_annual_comparison(
        portfolio_id=7,
        year=2024,
        canonical=canonical,
        legacy_months=legacy,
    )

    assert result.has_divergences is False
    assert result.monthly[0].kinds == (IntegratedFiscalComparisonKind.MATCH,)


def test_integrated_comparison_classifies_swing_and_day_trade_differences() -> None:
    canonical = _canonical(
        swing=(
            SimpleNamespace(
                competence_month="2024-06",
                realized_pnl_brl=Decimal(80),
                taxable_base_brl=Decimal(60),
                tax_due_brl=Decimal(9),
                loss_used_brl=Decimal(20),
            ),
        ),
        day_trade=(
            SimpleNamespace(
                competence_month="2024-06",
                realized_pnl_brl=Decimal(40),
                taxable_base_brl=Decimal(30),
                tax_due_brl=Decimal(6),
                loss_used_brl=Decimal(10),
            ),
        ),
    )
    legacy = [
        SimpleNamespace(
            mes="2024-06",
            lucro_swing_trade=100,
            base_calculo=100,
            ir_devido_swing=15,
            lucro_day_trade=50,
            ir_devido_day_trade=10,
        )
    ]

    item = build_integrated_annual_comparison(
        portfolio_id=7,
        year=2024,
        canonical=canonical,
        legacy_months=legacy,
    ).monthly[0]

    assert IntegratedFiscalComparisonKind.SWING_RESULT in item.kinds
    assert IntegratedFiscalComparisonKind.SWING_TAXABLE_BASE in item.kinds
    assert IntegratedFiscalComparisonKind.SWING_TAX_DUE in item.kinds
    assert IntegratedFiscalComparisonKind.DAY_TRADE_RESULT in item.kinds
    assert IntegratedFiscalComparisonKind.DAY_TRADE_TAXABLE_BASE in item.kinds
    assert IntegratedFiscalComparisonKind.DAY_TRADE_TAX_DUE in item.kinds
    assert IntegratedFiscalComparisonKind.LOSS_CARRYFORWARD in item.kinds


def test_integrated_comparison_classifies_missing_months() -> None:
    canonical = _canonical(
        day_trade=(
            SimpleNamespace(
                competence_month="2024-01",
                realized_pnl_brl=Decimal(10),
                taxable_base_brl=Decimal(10),
                tax_due_brl=Decimal(2),
                loss_used_brl=Decimal(0),
            ),
        )
    )
    legacy = [
        SimpleNamespace(
            mes="2024-02",
            lucro_swing_trade=0,
            base_calculo=0,
            ir_devido_swing=0,
            lucro_day_trade=5,
            ir_devido_day_trade=1,
        )
    ]

    result = build_integrated_annual_comparison(
        portfolio_id=7,
        year=2024,
        canonical=canonical,
        legacy_months=legacy,
    )

    assert IntegratedFiscalComparisonKind.LEGACY_MISSING_MONTH in result.monthly[0].kinds
    assert (
        IntegratedFiscalComparisonKind.CANONICAL_MISSING_MONTH
        in result.monthly[1].kinds
    )
