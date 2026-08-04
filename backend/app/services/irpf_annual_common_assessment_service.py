"""Serviço anual read-only de apuração fiscal de operações comuns.

O serviço orquestra apenas contratos canônicos já existentes: carrega baixas
realizadas, adapta políticas fiscais, agrega por mês, aplica isenção e compensa
prejuízos por grupo. Não calcula Day Trade, retenções, DARF mínima e não altera
o runtime legado nem contratos públicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.irpf_common_loss_carryforward import (
    FiscalMonthlyLossCompensation,
    compensate_common_losses,
)
from app.services.irpf_monthly_common_assessment import assess_common_monthly_groups
from app.services.irpf_realized_disposal_tax_adapter import (
    adapt_realized_disposals,
    group_common_entries_by_month,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup
from app.services.realized_pnl_projection_reader import load_realized_disposals


@dataclass(frozen=True)
class FiscalAnnualCommonAssessment:
    """Visão anual consolidada e auditável de operações comuns."""

    portfolio_id: int
    year: int
    start_date: date
    end_date: date
    monthly: tuple[FiscalMonthlyLossCompensation, ...]
    total_realized_pnl_brl: Decimal
    total_taxable_base_brl: Decimal
    total_tax_due_brl: Decimal
    closing_loss_carryforward_by_group: dict[TaxAssessmentGroup, Decimal]


def _annual_bounds(year: int) -> tuple[date, date]:
    if year < 1900 or year > 9999:
        raise ValueError("ano fiscal inválido")
    return date(year, 1, 1), date(year, 12, 31)


def build_annual_common_assessment(
    *,
    portfolio_id: int,
    year: int,
    monthly: tuple[FiscalMonthlyLossCompensation, ...]
    | list[FiscalMonthlyLossCompensation],
) -> FiscalAnnualCommonAssessment:
    """Consolida resultados mensais já compensados em uma visão anual."""

    start_date, end_date = _annual_bounds(year)
    ordered = tuple(
        sorted(monthly, key=lambda item: (item.competence_month, item.group.value))
    )
    expected_prefix = f"{year:04d}-"
    if any(not item.competence_month.startswith(expected_prefix) for item in ordered):
        raise ValueError("apuração mensal contém competência fora do ano fiscal")

    closing_by_group: dict[TaxAssessmentGroup, Decimal] = {}
    for item in ordered:
        closing_by_group[item.group] = item.closing_loss_carryforward_brl

    return FiscalAnnualCommonAssessment(
        portfolio_id=portfolio_id,
        year=year,
        start_date=start_date,
        end_date=end_date,
        monthly=ordered,
        total_realized_pnl_brl=sum(
            (item.realized_pnl_brl for item in ordered),
            start=Decimal(0),
        ),
        total_taxable_base_brl=sum(
            (item.taxable_base_brl for item in ordered),
            start=Decimal(0),
        ),
        total_tax_due_brl=sum(
            (item.tax_due_brl for item in ordered),
            start=Decimal(0),
        ),
        closing_loss_carryforward_by_group=closing_by_group,
    )


async def assess_annual_common_operations(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> FiscalAnnualCommonAssessment:
    """Executa o pipeline anual canônico de operações comuns."""

    start_date, end_date = _annual_bounds(year)
    disposals = await load_realized_disposals(
        db,
        portfolio_id,
        start_date=start_date,
        end_date=end_date,
    )
    entries = adapt_realized_disposals(disposals)
    groups = group_common_entries_by_month(entries)
    assessments = assess_common_monthly_groups(groups)
    compensated = compensate_common_losses(assessments)
    return build_annual_common_assessment(
        portfolio_id=portfolio_id,
        year=year,
        monthly=compensated,
    )
