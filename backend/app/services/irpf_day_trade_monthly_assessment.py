"""Apuração mensal read-only de Day Trade com compensação segregada."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection

_CENT = Decimal("0.01")
_DAY_TRADE_RATE = Decimal("0.20")


@dataclass(frozen=True)
class FiscalDayTradeMonthlyAssessment:
    competence_month: str
    matched_quantity: Decimal
    realized_pnl_brl: Decimal
    opening_loss_carryforward_brl: Decimal
    loss_used_brl: Decimal
    closing_loss_carryforward_brl: Decimal
    taxable_base_brl: Decimal
    tax_rate: Decimal
    tax_due_brl: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def assess_day_trade_months(
    projections: tuple[DayTradeMonthlyProjection, ...]
    | list[DayTradeMonthlyProjection],
) -> tuple[FiscalDayTradeMonthlyAssessment, ...]:
    """Apura Day Trade cronologicamente sem cruzar prejuízos com Swing Trade."""

    opening_loss = Decimal(0)
    result: list[FiscalDayTradeMonthlyAssessment] = []

    for projection in sorted(projections, key=lambda item: item.competence_month):
        realized = _money(projection.day_trade_result_brl)
        loss_used = Decimal(0)
        taxable_base = Decimal(0)

        if realized < 0:
            closing_loss = opening_loss + abs(realized)
        else:
            loss_used = min(opening_loss, realized)
            taxable_base = max(Decimal(0), realized - loss_used)
            closing_loss = opening_loss - loss_used

        tax_due = _money(taxable_base * _DAY_TRADE_RATE)
        result.append(
            FiscalDayTradeMonthlyAssessment(
                competence_month=projection.competence_month,
                matched_quantity=projection.matched_quantity,
                realized_pnl_brl=realized,
                opening_loss_carryforward_brl=_money(opening_loss),
                loss_used_brl=_money(loss_used),
                closing_loss_carryforward_brl=_money(closing_loss),
                taxable_base_brl=_money(taxable_base),
                tax_rate=_DAY_TRADE_RATE,
                tax_due_brl=tax_due,
            )
        )
        opening_loss = closing_loss

    return tuple(result)
