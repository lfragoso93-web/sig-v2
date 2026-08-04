"""Acumulação mensal read-only de imposto abaixo do limite mínimo de pagamento."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class FiscalMinimumPaymentAssessment:
    competence_month: str
    current_net_tax_due_brl: Decimal
    opening_accumulated_tax_brl: Decimal
    accumulated_tax_before_payment_brl: Decimal
    minimum_payment_threshold_brl: Decimal
    payment_due_brl: Decimal
    closing_accumulated_tax_brl: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def assess_minimum_payment(
    *,
    competence_month: str,
    current_net_tax_due_brl: Decimal,
    minimum_payment_threshold_brl: Decimal,
    opening_accumulated_tax_brl: Decimal = Decimal(0),
) -> FiscalMinimumPaymentAssessment:
    """Acumula imposto até atingir limite configurado de pagamento."""

    if current_net_tax_due_brl < 0:
        raise ValueError("imposto líquido do mês não pode ser negativo")
    if opening_accumulated_tax_brl < 0:
        raise ValueError("saldo acumulado não pode ser negativo")
    if minimum_payment_threshold_brl <= 0:
        raise ValueError("limite mínimo de pagamento deve ser positivo")

    current = _money(current_net_tax_due_brl)
    opening = _money(opening_accumulated_tax_brl)
    threshold = _money(minimum_payment_threshold_brl)
    accumulated = _money(opening + current)
    payment_due = accumulated if accumulated >= threshold else Decimal("0.00")
    closing = Decimal("0.00") if payment_due > 0 else accumulated

    return FiscalMinimumPaymentAssessment(
        competence_month=competence_month,
        current_net_tax_due_brl=current,
        opening_accumulated_tax_brl=opening,
        accumulated_tax_before_payment_brl=accumulated,
        minimum_payment_threshold_brl=threshold,
        payment_due_brl=_money(payment_due),
        closing_accumulated_tax_brl=_money(closing),
    )


def assess_minimum_payments(
    *,
    monthly_net_tax_due: tuple[tuple[str, Decimal], ...]
    | list[tuple[str, Decimal]],
    minimum_payment_threshold_brl: Decimal,
) -> tuple[FiscalMinimumPaymentAssessment, ...]:
    """Avalia competências em ordem cronológica e transporta o saldo acumulado."""

    opening = Decimal(0)
    result: list[FiscalMinimumPaymentAssessment] = []
    for competence_month, current_net_tax_due_brl in sorted(monthly_net_tax_due):
        assessment = assess_minimum_payment(
            competence_month=competence_month,
            current_net_tax_due_brl=current_net_tax_due_brl,
            minimum_payment_threshold_brl=minimum_payment_threshold_brl,
            opening_accumulated_tax_brl=opening,
        )
        result.append(assessment)
        opening = assessment.closing_accumulated_tax_brl
    return tuple(result)
