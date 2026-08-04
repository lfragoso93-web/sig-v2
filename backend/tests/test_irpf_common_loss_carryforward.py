"""Testes da compensação segregada de prejuízos em operações comuns."""

from decimal import Decimal

from app.services.irpf_common_loss_carryforward import compensate_common_losses
from app.services.irpf_monthly_common_assessment import FiscalMonthlyAssessment
from app.services.irpf_tax_policy import TaxAssessmentGroup


def _assessment(
    *,
    month: str,
    group: TaxAssessmentGroup,
    pnl: str,
    tax_rate: str,
    exemption_applied: bool = False,
) -> FiscalMonthlyAssessment:
    pnl_value = Decimal(pnl)
    taxable = Decimal(0) if exemption_applied else max(Decimal(0), pnl_value)
    return FiscalMonthlyAssessment(
        competence_month=month,
        group=group,
        gross_proceeds_brl=Decimal(0),
        realized_pnl_brl=pnl_value,
        exemption_limit_brl=Decimal(20000) if group is TaxAssessmentGroup.STOCKS else None,
        exemption_applied=exemption_applied,
        taxable_base_brl=taxable,
        tax_rate=Decimal(tax_rate),
        tax_due_brl=(taxable * Decimal(tax_rate)).quantize(Decimal("0.01")),
    )


def test_loss_is_carried_and_fully_consumed_in_same_group() -> None:
    results = compensate_common_losses(
        [
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.ETF,
                pnl="-1000",
                tax_rate="0.15",
            ),
            _assessment(
                month="2024-02",
                group=TaxAssessmentGroup.ETF,
                pnl="1600",
                tax_rate="0.15",
            ),
        ]
    )

    assert results[0].closing_loss_carryforward_brl == Decimal(1000)
    assert results[1].opening_loss_carryforward_brl == Decimal(1000)
    assert results[1].loss_used_brl == Decimal(1000)
    assert results[1].taxable_base_brl == Decimal(600)
    assert results[1].tax_due_brl == Decimal("90.00")
    assert results[1].closing_loss_carryforward_brl == Decimal(0)


def test_loss_is_partially_consumed_and_remaining_balance_is_preserved() -> None:
    results = compensate_common_losses(
        [
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.BDR,
                pnl="-1000",
                tax_rate="0.15",
            ),
            _assessment(
                month="2024-02",
                group=TaxAssessmentGroup.BDR,
                pnl="400",
                tax_rate="0.15",
            ),
        ]
    )

    assert results[1].loss_used_brl == Decimal(400)
    assert results[1].taxable_base_brl == Decimal(0)
    assert results[1].tax_due_brl == Decimal("0.00")
    assert results[1].closing_loss_carryforward_brl == Decimal(600)


def test_losses_do_not_cross_tax_groups() -> None:
    results = compensate_common_losses(
        [
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.STOCKS,
                pnl="-1000",
                tax_rate="0.15",
            ),
            _assessment(
                month="2024-02",
                group=TaxAssessmentGroup.BDR,
                pnl="1000",
                tax_rate="0.15",
            ),
        ]
    )

    assert results[1].opening_loss_carryforward_brl == Decimal(0)
    assert results[1].loss_used_brl == Decimal(0)
    assert results[1].taxable_base_brl == Decimal(1000)
    assert results[1].tax_due_brl == Decimal("150.00")


def test_exempt_stock_profit_does_not_consume_loss_balance() -> None:
    results = compensate_common_losses(
        [
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.STOCKS,
                pnl="-800",
                tax_rate="0.15",
            ),
            _assessment(
                month="2024-02",
                group=TaxAssessmentGroup.STOCKS,
                pnl="500",
                tax_rate="0.15",
                exemption_applied=True,
            ),
            _assessment(
                month="2024-03",
                group=TaxAssessmentGroup.STOCKS,
                pnl="1000",
                tax_rate="0.15",
            ),
        ]
    )

    assert results[1].opening_loss_carryforward_brl == Decimal(800)
    assert results[1].loss_used_brl == Decimal(0)
    assert results[1].closing_loss_carryforward_brl == Decimal(800)
    assert results[2].loss_used_brl == Decimal(800)
    assert results[2].taxable_base_brl == Decimal(200)
    assert results[2].tax_due_brl == Decimal("30.00")


def test_additional_losses_accumulate_within_group() -> None:
    results = compensate_common_losses(
        [
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.REAL_ESTATE_FUNDS,
                pnl="-250",
                tax_rate="0.20",
            ),
            _assessment(
                month="2024-02",
                group=TaxAssessmentGroup.REAL_ESTATE_FUNDS,
                pnl="-150",
                tax_rate="0.20",
            ),
        ]
    )

    assert results[0].closing_loss_carryforward_brl == Decimal(250)
    assert results[1].opening_loss_carryforward_brl == Decimal(250)
    assert results[1].closing_loss_carryforward_brl == Decimal(400)


def test_results_are_sorted_by_month_and_group() -> None:
    results = compensate_common_losses(
        [
            _assessment(
                month="2024-02",
                group=TaxAssessmentGroup.ETF,
                pnl="100",
                tax_rate="0.15",
            ),
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.STOCKS,
                pnl="100",
                tax_rate="0.15",
            ),
            _assessment(
                month="2024-01",
                group=TaxAssessmentGroup.BDR,
                pnl="100",
                tax_rate="0.15",
            ),
        ]
    )

    assert [(item.competence_month, item.group) for item in results] == [
        ("2024-01", TaxAssessmentGroup.BDR),
        ("2024-01", TaxAssessmentGroup.STOCKS),
        ("2024-02", TaxAssessmentGroup.ETF),
    ]
