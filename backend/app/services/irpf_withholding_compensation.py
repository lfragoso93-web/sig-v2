"""Compensação mensal e segregada de IRRF no motor canônico do IRPF."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.irpf_withholding_policy import WithholdingOperationKind

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class FiscalMonthlyWithholdingCompensation:
    competence_month: str
    operation_kind: WithholdingOperationKind
    gross_tax_due_brl: Decimal
    current_withholding_brl: Decimal
    opening_withholding_balance_brl: Decimal
    withholding_used_brl: Decimal
    closing_withholding_balance_brl: Decimal
    net_tax_due_brl: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def compensate_withholding(
    *,
    competence_month: str,
    operation_kind: WithholdingOperationKind,
    gross_tax_due_brl: Decimal,
    current_withholding_brl: Decimal,
    opening_withholding_balance_brl: Decimal = Decimal(0),
) -> FiscalMonthlyWithholdingCompensation:
    """Compensa IRRF sem cruzar buckets comuns e Day Trade."""

    for value, label in (
        (gross_tax_due_brl, "imposto devido"),
        (current_withholding_brl, "IRRF do mês"),
        (opening_withholding_balance_brl, "saldo inicial de IRRF"),
    ):
        if value < 0:
            raise ValueError(f"{label} não pode ser negativo")

    gross_tax = _money(gross_tax_due_brl)
    current = _money(current_withholding_brl)
    opening = _money(opening_withholding_balance_brl)
    available = opening + current
    used = min(gross_tax, available)
    closing = available - used
    net_tax = gross_tax - used

    return FiscalMonthlyWithholdingCompensation(
        competence_month=competence_month,
        operation_kind=operation_kind,
        gross_tax_due_brl=gross_tax,
        current_withholding_brl=current,
        opening_withholding_balance_brl=opening,
        withholding_used_brl=_money(used),
        closing_withholding_balance_brl=_money(closing),
        net_tax_due_brl=_money(net_tax),
    )
