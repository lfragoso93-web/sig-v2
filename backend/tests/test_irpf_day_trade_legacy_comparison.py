"""Testes do comparador quantitativo Day Trade canônico × legado."""

from decimal import Decimal

from app.services.irpf_day_trade_legacy_comparison import (
    DayTradeDivergenceKind,
    LegacyDayTradeMonth,
    compare_day_trade_months,
)
from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection


def _canonical(
    month: str,
    quantity: str,
    result: str,
) -> DayTradeMonthlyProjection:
    return DayTradeMonthlyProjection(
        competence_month=month,
        matched_quantity=Decimal(quantity),
        day_trade_result_brl=Decimal(result),
        unmatched_buy_quantity=Decimal(0),
        unmatched_sell_quantity=Decimal(0),
        matches=(),
    )


def _legacy(month: str, quantity: str, result: str) -> LegacyDayTradeMonth:
    return LegacyDayTradeMonth(
        competence_month=month,
        matched_quantity=Decimal(quantity),
        day_trade_result_brl=Decimal(result),
    )


def test_comparison_marks_equivalent_month_as_match() -> None:
    [comparison] = compare_day_trade_months(
        [_canonical("2024-05", "5", "10")],
        [_legacy("2024-05", "5", "10")],
    )

    assert comparison.is_match
    assert comparison.kinds == (DayTradeDivergenceKind.MATCH,)
    assert comparison.quantity_delta == Decimal(0)
    assert comparison.result_delta_brl == Decimal(0)


def test_comparison_classifies_quantity_and_result_differences() -> None:
    [comparison] = compare_day_trade_months(
        [_canonical("2024-05", "5", "10")],
        [_legacy("2024-05", "20", "40")],
    )

    assert comparison.kinds == (
        DayTradeDivergenceKind.QUANTITY,
        DayTradeDivergenceKind.RESULT,
    )
    assert comparison.quantity_delta == Decimal(-15)
    assert comparison.result_delta_brl == Decimal(-30)


def test_comparison_classifies_missing_months() -> None:
    comparisons = compare_day_trade_months(
        [_canonical("2024-05", "5", "10")],
        [_legacy("2024-06", "2", "3")],
    )

    assert comparisons[0].kinds == (
        DayTradeDivergenceKind.LEGACY_MISSING_MONTH,
        DayTradeDivergenceKind.QUANTITY,
        DayTradeDivergenceKind.RESULT,
    )
    assert comparisons[1].kinds == (
        DayTradeDivergenceKind.CANONICAL_MISSING_MONTH,
        DayTradeDivergenceKind.QUANTITY,
        DayTradeDivergenceKind.RESULT,
    )
