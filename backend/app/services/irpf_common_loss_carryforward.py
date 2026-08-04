"""Compensação mensal read-only de prejuízos por grupo fiscal.

Este módulo consome apurações mensais de operações comuns e carrega prejuízos
exclusivamente dentro do mesmo grupo fiscal. Não calcula Day Trade, retenções,
DARF mínima nem substitui o runtime legado.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.irpf_monthly_common_assessment import FiscalMonthlyAssessment
from app.services.irpf_tax_policy import TaxAssessmentGroup

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class FiscalMonthlyLossCompensation:
    """Resultado mensal após compensação segregada de prejuízos."""

    competence_month: str
    group: TaxAssessmentGroup
    realized_pnl_brl: Decimal
    exemption_applied: bool
    opening_loss_carryforward_brl: Decimal
    loss_used_brl: Decimal
    closing_loss_carryforward_brl: Decimal
    taxable_base_brl: Decimal
    tax_rate: Decimal
    tax_due_brl: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def compensate_common_losses(
    assessments: tuple[FiscalMonthlyAssessment, ...]
    | list[FiscalMonthlyAssessment],
) -> tuple[FiscalMonthlyLossCompensation, ...]:
    """Compensa prejuízos cronologicamente sem cruzar grupos fiscais."""

    ordered = sorted(
        assessments,
        key=lambda item: (item.competence_month, item.group.value),
    )
    carryforward: dict[TaxAssessmentGroup, Decimal] = defaultdict(Decimal)
    result: list[FiscalMonthlyLossCompensation] = []

    for assessment in ordered:
        opening = carryforward[assessment.group]
        realized = assessment.realized_pnl_brl
        loss_used = Decimal(0)
        taxable_base = Decimal(0)

        if assessment.exemption_applied:
            closing = opening
        elif realized < 0:
            closing = opening + abs(realized)
        else:
            loss_used = min(opening, realized)
            taxable_base = max(Decimal(0), realized - loss_used)
            closing = opening - loss_used

        tax_due = _money(taxable_base * assessment.tax_rate)
        carryforward[assessment.group] = closing
        result.append(
            FiscalMonthlyLossCompensation(
                competence_month=assessment.competence_month,
                group=assessment.group,
                realized_pnl_brl=_money(realized),
                exemption_applied=assessment.exemption_applied,
                opening_loss_carryforward_brl=_money(opening),
                loss_used_brl=_money(loss_used),
                closing_loss_carryforward_brl=_money(closing),
                taxable_base_brl=_money(taxable_base),
                tax_rate=assessment.tax_rate,
                tax_due_brl=tax_due,
            )
        )

    return tuple(result)
