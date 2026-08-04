"""Apuração anual read-only integrada de Day Trade e excedentes Swing.

Este serviço compõe contratos canônicos existentes sem alterar o runtime legado.
Ele carrega transações e baixas uma única vez, separa quantitativamente Day Trade,
filtra as baixas Swing e reaproveita política, isenção e compensação já canônicas.
"""

from __future__ import annotations

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
from app.services.irpf_day_trade_monthly_projection import (
    DayTradeMonthlyProjection,
    project_day_trades_by_month,
)
from app.services.irpf_day_trade_transaction_adapter import adapt_ordered_transactions
from app.services.irpf_monthly_common_assessment import assess_common_monthly_groups
from app.services.irpf_realized_disposal_tax_adapter import (
    adapt_realized_disposals,
    group_common_entries_by_month,
)
from app.services.irpf_swing_remainder_projection import (
    project_swing_remainder_disposals,
)
from app.services.realized_pnl_projection_reader import load_realized_disposals


@dataclass(frozen=True)
class FiscalAnnualIntegratedAssessment:
    portfolio_id: int
    year: int
    start_date: date
    end_date: date
    day_trade_monthly: tuple[DayTradeMonthlyProjection, ...]
    swing: FiscalAnnualCommonAssessment
    total_day_trade_result_brl: Decimal
    total_swing_realized_pnl_brl: Decimal
    total_swing_taxable_base_brl: Decimal
    total_swing_tax_due_brl: Decimal


def _annual_bounds(year: int) -> tuple[date, date]:
    if year < 1900 or year > 9999:
        raise ValueError("ano fiscal inválido")
    return date(year, 1, 1), date(year, 12, 31)


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
    day_trade_monthly = project_day_trades_by_month(operations)
    matches = tuple(
        match
        for month in day_trade_monthly
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

    return FiscalAnnualIntegratedAssessment(
        portfolio_id=portfolio_id,
        year=year,
        start_date=start_date,
        end_date=end_date,
        day_trade_monthly=day_trade_monthly,
        swing=swing,
        total_day_trade_result_brl=sum(
            (item.day_trade_result_brl for item in day_trade_monthly),
            start=Decimal(0),
        ),
        total_swing_realized_pnl_brl=swing.total_realized_pnl_brl,
        total_swing_taxable_base_brl=swing.total_taxable_base_brl,
        total_swing_tax_due_brl=swing.total_tax_due_brl,
    )
