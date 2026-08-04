"""Apuração mensal read-only de operações comuns por grupo fiscal.

Este módulo consome agregações fiscais derivadas de baixas canônicas e aplica
somente alíquota e isenção mensal por política. Não compensa prejuízos, não
calcula Day Trade, não aplica retenções e não substitui o runtime legado.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.irpf_realized_disposal_tax_adapter import FiscalMonthlyGroup
from app.services.irpf_tax_policy import TaxAssessmentGroup

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class FiscalMonthlyAssessment:
    """Resultado mensal de operação comum para um único grupo fiscal."""

    competence_month: str
    group: TaxAssessmentGroup
    gross_proceeds_brl: Decimal
    realized_pnl_brl: Decimal
    exemption_limit_brl: Decimal | None
    exemption_applied: bool
    taxable_base_brl: Decimal
    tax_rate: Decimal
    tax_due_brl: Decimal


def _money(value: Decimal) -> Decimal:
    """Arredonda valores monetários para centavos de forma determinística."""

    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def assess_common_monthly_group(
    group: FiscalMonthlyGroup,
) -> FiscalMonthlyAssessment:
    """Aplica a política fiscal comum sem compensação de prejuízos."""

    if not group.entries:
        raise ValueError("grupo fiscal mensal sem entradas")

    first_policy = group.entries[0].policy
    if first_policy.common_group is not group.group:
        raise ValueError("grupo mensal incompatível com a política fiscal")
    if any(entry.policy != first_policy for entry in group.entries):
        raise ValueError("grupo mensal contém políticas fiscais divergentes")

    exemption_limit = first_policy.monthly_exemption_limit
    exemption_applied = (
        exemption_limit is not None
        and group.gross_proceeds_brl <= exemption_limit
    )
    taxable_base = (
        Decimal(0)
        if exemption_applied
        else max(Decimal(0), group.realized_pnl_brl)
    )
    tax_due = _money(taxable_base * first_policy.common_rate)

    return FiscalMonthlyAssessment(
        competence_month=group.competence_month,
        group=group.group,
        gross_proceeds_brl=_money(group.gross_proceeds_brl),
        realized_pnl_brl=_money(group.realized_pnl_brl),
        exemption_limit_brl=exemption_limit,
        exemption_applied=exemption_applied,
        taxable_base_brl=_money(taxable_base),
        tax_rate=first_policy.common_rate,
        tax_due_brl=tax_due,
    )


def assess_common_monthly_groups(
    groups: tuple[FiscalMonthlyGroup, ...] | list[FiscalMonthlyGroup],
) -> tuple[FiscalMonthlyAssessment, ...]:
    """Apura e ordena grupos mensais sem misturar classes ou meses."""

    return tuple(
        sorted(
            (assess_common_monthly_group(group) for group in groups),
            key=lambda item: (item.competence_month, item.group.value),
        )
    )
