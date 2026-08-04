"""Testes da apuração mensal canônica de Day Trade."""

from decimal import Decimal

from app.services.irpf_day_trade_monthly_assessment import assess_day_trade_months
from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection


def _projection(month: str, result: str) -> DayTradeMonthlyProjection:
    return DayTradeMonthlyProjection(
        competence_month=month,
        matched_quantity=Decimal(10),
        day_trade_result_brl=Decimal(result),
        unmatched_buy_quantity=Decimal(0),
        unmatched_sell_quantity=Decimal(0),
        matches=(),
    )


def test_positive_day_trade_result_is_taxed_at_twenty_percent() -> None:
    assessment = assess_day_trade_months([_projection("2024-01", "100.00")])[0]

    assert assessment.tax_rate == Decimal("0.20")
    assert assessment.taxable_base_brl == Decimal("100.00")
    assert assessment.tax_due_brl == Decimal("20.00")
    assert assessment.closing_loss_carryforward_brl == Decimal("0.00")


def test_day_trade_loss_is_carried_only_in_day_trade_bucket() -> None:
    assessment = assess_day_trade_months([_projection("2024-01", "-80.00")])[0]

    assert assessment.taxable_base_brl == Decimal("0.00")
    assert assessment.tax_due_brl == Decimal("0.00")
    assert assessment.closing_loss_carryforward_brl == Decimal("80.00")


def test_later_profit_consumes_day_trade_loss_before_tax() -> None:
    assessments = assess_day_trade_months(
        [
            _projection("2024-01", "-80.00"),
            _projection("2024-02", "100.00"),
        ]
    )

    february = assessments[1]
    assert february.opening_loss_carryforward_brl == Decimal("80.00")
    assert february.loss_used_brl == Decimal("80.00")
    assert february.taxable_base_brl == Decimal("20.00")
    assert february.tax_due_brl == Decimal("4.00")
    assert february.closing_loss_carryforward_brl == Decimal("0.00")


def test_assessment_orders_competences_before_compensation() -> None:
    assessments = assess_day_trade_months(
        [
            _projection("2024-02", "100.00"),
            _projection("2024-01", "-40.00"),
        ]
    )

    assert [item.competence_month for item in assessments] == ["2024-01", "2024-02"]
    assert assessments[1].taxable_base_brl == Decimal("60.00")
    assert assessments[1].tax_due_brl == Decimal("12.00")
