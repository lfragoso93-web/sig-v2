"""Mapper puro da apuração anual integrada para o contrato versionado v1."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.services.irpf_annual_assessment_contract import (
    IRPF_ANNUAL_ASSESSMENT_SCHEMA_VERSION,
    IrpfAnnualAssessmentContract,
    IrpfMonthlyAssessmentContract,
)
from app.services.irpf_annual_integrated_assessment_service import (
    FiscalAnnualIntegratedAssessment,
)


def build_irpf_annual_assessment_contract(
    assessment: FiscalAnnualIntegratedAssessment,
) -> IrpfAnnualAssessmentContract:
    """Projeta a apuração operacional no contrato interno estável v1."""

    swing_gross: dict[str, Decimal] = defaultdict(Decimal)
    swing_withholding: dict[str, Decimal] = defaultdict(Decimal)
    swing_net: dict[str, Decimal] = defaultdict(Decimal)
    day_trade_gross: dict[str, Decimal] = defaultdict(Decimal)
    day_trade_withholding: dict[str, Decimal] = defaultdict(Decimal)
    day_trade_net: dict[str, Decimal] = defaultdict(Decimal)
    payment_due: dict[str, Decimal] = defaultdict(Decimal)
    closing_accumulated: dict[str, Decimal] = defaultdict(Decimal)

    for item in assessment.swing.monthly:
        swing_gross[item.competence_month] += item.tax_due_brl
    for item in assessment.common_withholding_monthly:
        swing_withholding[item.competence_month] += item.withholding_used_brl
        swing_net[item.competence_month] += item.net_tax_due_brl
    for item in assessment.day_trade_monthly:
        day_trade_gross[item.competence_month] += item.tax_due_brl
    for item in assessment.day_trade_withholding_monthly:
        day_trade_withholding[item.competence_month] += item.withholding_used_brl
        day_trade_net[item.competence_month] += item.net_tax_due_brl
    for item in assessment.minimum_payment_monthly:
        payment_due[item.competence_month] += item.payment_due_brl
        closing_accumulated[item.competence_month] = item.closing_accumulated_tax_brl

    months = sorted(
        set(swing_gross)
        | set(swing_net)
        | set(day_trade_gross)
        | set(day_trade_net)
        | set(payment_due)
    )
    monthly = tuple(
        IrpfMonthlyAssessmentContract(
            competence_month=month,
            swing_gross_tax_due_brl=swing_gross[month],
            swing_withholding_brl=swing_withholding[month],
            swing_net_tax_due_brl=swing_net[month],
            day_trade_gross_tax_due_brl=day_trade_gross[month],
            day_trade_withholding_brl=day_trade_withholding[month],
            day_trade_net_tax_due_brl=day_trade_net[month],
            total_net_tax_due_brl=swing_net[month] + day_trade_net[month],
            payment_due_brl=payment_due[month],
            closing_accumulated_tax_brl=closing_accumulated[month],
        )
        for month in months
    )
    total_withholding = sum(
        (
            item.withholding_used_brl
            for item in (
                *assessment.common_withholding_monthly,
                *assessment.day_trade_withholding_monthly,
            )
        ),
        start=Decimal(0),
    )

    return IrpfAnnualAssessmentContract(
        schema_version=IRPF_ANNUAL_ASSESSMENT_SCHEMA_VERSION,
        portfolio_id=assessment.portfolio_id,
        year=assessment.year,
        monthly=monthly,
        total_gross_tax_due_brl=assessment.total_tax_due_brl,
        total_withholding_brl=total_withholding,
        total_net_tax_due_brl=assessment.total_net_tax_due_brl,
        total_payment_due_brl=assessment.total_payment_due_brl,
        closing_accumulated_tax_brl=assessment.closing_accumulated_tax_brl,
        closing_common_withholding_balance_brl=(
            assessment.closing_common_withholding_balance_brl
        ),
        closing_day_trade_withholding_balance_brl=(
            assessment.closing_day_trade_withholding_balance_brl
        ),
        closing_day_trade_loss_carryforward_brl=(
            assessment.closing_day_trade_loss_carryforward_brl
        ),
    )
