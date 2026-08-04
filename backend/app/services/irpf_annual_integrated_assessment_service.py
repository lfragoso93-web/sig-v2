"""Apuração anual read-only integrada de Day Trade e excedentes Swing.

Este serviço compõe contratos canônicos existentes sem alterar o runtime legado.
Ele carrega transações e baixas uma única vez, separa quantitativamente Day Trade,
filtra as baixas Swing e reaproveita política, isenção, compensação, IRRF e
acumulação mínima de DARF.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.irpf_annual_common_assessment_service import (
    FiscalAnnualCommonAssessment,
    build_annual_common_assessment,
)
from app.services.irpf_common_loss_carryforward import compensate_common_losses
from app.services.irpf_day_trade_monthly_assessment import (
    FiscalDayTradeMonthlyAssessment,
    assess_day_trade_months,
)
from app.services.irpf_day_trade_monthly_projection import project_day_trades_by_month
from app.services.irpf_day_trade_transaction_adapter import adapt_ordered_transactions
from app.services.irpf_minimum_payment_accumulation import (
    FiscalMinimumPaymentAssessment,
    assess_minimum_payments,
)
from app.services.irpf_minimum_payment_policy import MINIMUM_DARF_PAYMENT_BRL
from app.services.irpf_monthly_common_assessment import assess_common_monthly_groups
from app.services.irpf_realized_disposal_tax_adapter import (
    adapt_realized_disposals,
    group_common_entries_by_month,
)
from app.services.irpf_swing_remainder_projection import (
    project_swing_remainder_disposals,
)
from app.services.irpf_withholding_compensation import (
    FiscalMonthlyWithholdingCompensation,
    compensate_withholding,
)
from app.services.irpf_withholding_policy import (
    WithholdingOperationKind,
    assess_common_withholding,
    assess_day_trade_withholding,
)
from app.services.realized_pnl_projection_reader import load_realized_disposals


@dataclass(frozen=True)
class FiscalAnnualIntegratedAssessment:
    portfolio_id: int
    year: int
    start_date: date
    end_date: date
    day_trade_monthly: tuple[FiscalDayTradeMonthlyAssessment, ...]
    swing: FiscalAnnualCommonAssessment
    common_withholding_monthly: tuple[FiscalMonthlyWithholdingCompensation, ...]
    day_trade_withholding_monthly: tuple[
        FiscalMonthlyWithholdingCompensation, ...
    ]
    minimum_payment_monthly: tuple[FiscalMinimumPaymentAssessment, ...]
    total_day_trade_result_brl: Decimal
    total_day_trade_taxable_base_brl: Decimal
    total_day_trade_tax_due_brl: Decimal
    total_day_trade_net_tax_due_brl: Decimal
    closing_day_trade_loss_carryforward_brl: Decimal
    closing_day_trade_withholding_balance_brl: Decimal
    total_swing_realized_pnl_brl: Decimal
    total_swing_taxable_base_brl: Decimal
    total_swing_tax_due_brl: Decimal
    total_swing_net_tax_due_brl: Decimal
    closing_common_withholding_balance_brl: Decimal
    total_tax_due_brl: Decimal
    total_net_tax_due_brl: Decimal
    total_payment_due_brl: Decimal
    closing_accumulated_tax_brl: Decimal


def _annual_bounds(year: int) -> tuple[date, date]:
    if year < 1900 or year > 9999:
        raise ValueError("ano fiscal inválido")
    return date(year, 1, 1), date(year, 12, 31)


def _compensate_common_withholding(
    swing_groups: tuple,
    swing_monthly: tuple,
) -> tuple[FiscalMonthlyWithholdingCompensation, ...]:
    gross_sales_by_month: dict[str, Decimal] = defaultdict(Decimal)
    tax_due_by_month: dict[str, Decimal] = defaultdict(Decimal)
    for group in swing_groups:
        gross_sales_by_month[group.competence_month] += group.gross_proceeds_brl
    for assessment in swing_monthly:
        tax_due_by_month[assessment.competence_month] += assessment.tax_due_brl

    balance = Decimal(0)
    result: list[FiscalMonthlyWithholdingCompensation] = []
    for month in sorted(set(gross_sales_by_month) | set(tax_due_by_month)):
        withholding = assess_common_withholding(
            competence_month=month,
            gross_sales_brl=gross_sales_by_month[month],
        )
        compensation = compensate_withholding(
            competence_month=month,
            operation_kind=WithholdingOperationKind.COMMON,
            gross_tax_due_brl=tax_due_by_month[month],
            current_withholding_brl=withholding.withholding_tax_brl,
            opening_withholding_balance_brl=balance,
        )
        balance = compensation.closing_withholding_balance_brl
        result.append(compensation)
    return tuple(result)


def _compensate_day_trade_withholding(
    day_trade_monthly: tuple[FiscalDayTradeMonthlyAssessment, ...],
) -> tuple[FiscalMonthlyWithholdingCompensation, ...]:
    balance = Decimal(0)
    result: list[FiscalMonthlyWithholdingCompensation] = []
    for assessment in day_trade_monthly:
        withholding = assess_day_trade_withholding(
            competence_month=assessment.competence_month,
            net_day_trade_result_brl=assessment.realized_pnl_brl,
        )
        compensation = compensate_withholding(
            competence_month=assessment.competence_month,
            operation_kind=WithholdingOperationKind.DAY_TRADE,
            gross_tax_due_brl=assessment.tax_due_brl,
            current_withholding_brl=withholding.withholding_tax_brl,
            opening_withholding_balance_brl=balance,
        )
        balance = compensation.closing_withholding_balance_brl
        result.append(compensation)
    return tuple(result)


def _assess_minimum_darf_payments(
    common_monthly: tuple[FiscalMonthlyWithholdingCompensation, ...],
    day_trade_monthly: tuple[FiscalMonthlyWithholdingCompensation, ...],
) -> tuple[FiscalMinimumPaymentAssessment, ...]:
    net_tax_by_month: dict[str, Decimal] = defaultdict(Decimal)
    for assessment in (*common_monthly, *day_trade_monthly):
        net_tax_by_month[assessment.competence_month] += assessment.net_tax_due_brl
    return assess_minimum_payments(
        monthly_net_tax_due=tuple(net_tax_by_month.items()),
        minimum_payment_threshold_brl=MINIMUM_DARF_PAYMENT_BRL,
    )


async def assess_annual_integrated_operations(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> FiscalAnnualIntegratedAssessment:
    """Executa o pipeline anual integrado sem persistência ou troca de runtime."""

    start_date, end_date = _annual_bounds(year)
    tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = tx_result.scalars().all()
    operations = adapt_ordered_transactions(transactions)
    day_trade_projection = project_day_trades_by_month(operations)
    day_trade_monthly = assess_day_trade_months(day_trade_projection)
    matches = tuple(
        match
        for month in day_trade_projection
        for match in month.matches
    )

    disposals = await load_realized_disposals(
        db,
        portfolio_id,
        start_date=start_date,
        end_date=end_date,
    )
    swing_disposals = project_swing_remainder_disposals(disposals, matches)
    swing_entries = adapt_realized_disposals(swing_disposals)
    swing_groups = group_common_entries_by_month(swing_entries)
    swing_assessments = assess_common_monthly_groups(swing_groups)
    swing_compensated = compensate_common_losses(swing_assessments)
    swing = build_annual_common_assessment(
        portfolio_id=portfolio_id,
        year=year,
        monthly=swing_compensated,
    )

    common_withholding_monthly = _compensate_common_withholding(
        swing_groups,
        swing.monthly,
    )
    day_trade_withholding_monthly = _compensate_day_trade_withholding(
        day_trade_monthly
    )
    minimum_payment_monthly = _assess_minimum_darf_payments(
        common_withholding_monthly,
        day_trade_withholding_monthly,
    )

    total_day_trade_result = sum(
        (item.realized_pnl_brl for item in day_trade_monthly),
        start=Decimal(0),
    )
    total_day_trade_taxable_base = sum(
        (item.taxable_base_brl for item in day_trade_monthly),
        start=Decimal(0),
    )
    total_day_trade_tax_due = sum(
        (item.tax_due_brl for item in day_trade_monthly),
        start=Decimal(0),
    )
    total_day_trade_net_tax_due = sum(
        (item.net_tax_due_brl for item in day_trade_withholding_monthly),
        start=Decimal(0),
    )
    closing_day_trade_loss = (
        day_trade_monthly[-1].closing_loss_carryforward_brl
        if day_trade_monthly
        else Decimal(0)
    )
    closing_day_trade_withholding = (
        day_trade_withholding_monthly[-1].closing_withholding_balance_brl
        if day_trade_withholding_monthly
        else Decimal(0)
    )
    total_swing_net_tax_due = sum(
        (item.net_tax_due_brl for item in common_withholding_monthly),
        start=Decimal(0),
    )
    closing_common_withholding = (
        common_withholding_monthly[-1].closing_withholding_balance_brl
        if common_withholding_monthly
        else Decimal(0)
    )
    total_payment_due = sum(
        (item.payment_due_brl for item in minimum_payment_monthly),
        start=Decimal(0),
    )
    closing_accumulated_tax = (
        minimum_payment_monthly[-1].closing_accumulated_tax_brl
        if minimum_payment_monthly
        else Decimal(0)
    )

    return FiscalAnnualIntegratedAssessment(
        portfolio_id=portfolio_id,
        year=year,
        start_date=start_date,
        end_date=end_date,
        day_trade_monthly=day_trade_monthly,
        swing=swing,
        common_withholding_monthly=common_withholding_monthly,
        day_trade_withholding_monthly=day_trade_withholding_monthly,
        minimum_payment_monthly=minimum_payment_monthly,
        total_day_trade_result_brl=total_day_trade_result,
        total_day_trade_taxable_base_brl=total_day_trade_taxable_base,
        total_day_trade_tax_due_brl=total_day_trade_tax_due,
        total_day_trade_net_tax_due_brl=total_day_trade_net_tax_due,
        closing_day_trade_loss_carryforward_brl=closing_day_trade_loss,
        closing_day_trade_withholding_balance_brl=closing_day_trade_withholding,
        total_swing_realized_pnl_brl=swing.total_realized_pnl_brl,
        total_swing_taxable_base_brl=swing.total_taxable_base_brl,
        total_swing_tax_due_brl=swing.total_tax_due_brl,
        total_swing_net_tax_due_brl=total_swing_net_tax_due,
        closing_common_withholding_balance_brl=closing_common_withholding,
        total_tax_due_brl=total_day_trade_tax_due + swing.total_tax_due_brl,
        total_net_tax_due_brl=(
            total_day_trade_net_tax_due + total_swing_net_tax_due
        ),
        total_payment_due_brl=total_payment_due,
        closing_accumulated_tax_brl=closing_accumulated_tax,
    )
