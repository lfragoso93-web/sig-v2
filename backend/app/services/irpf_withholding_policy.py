"""Política canônica e read-only de IRRF para renda variável."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

_CENT = Decimal("0.01")
_COMMON_WITHHOLDING_RATE = Decimal("0.00005")
_DAY_TRADE_WITHHOLDING_RATE = Decimal("0.01")


class WithholdingOperationKind(StrEnum):
    COMMON = "common"
    DAY_TRADE = "day_trade"


@dataclass(frozen=True)
class FiscalWithholdingAssessment:
    competence_month: str
    operation_kind: WithholdingOperationKind
    calculation_base_brl: Decimal
    withholding_rate: Decimal
    withholding_tax_brl: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def assess_common_withholding(
    *,
    competence_month: str,
    gross_sales_brl: Decimal,
) -> FiscalWithholdingAssessment:
    """Calcula IRRF de operações comuns sobre o valor bruto das vendas."""

    if gross_sales_brl < 0:
        raise ValueError("valor bruto de vendas não pode ser negativo")
    base = _money(gross_sales_brl)
    return FiscalWithholdingAssessment(
        competence_month=competence_month,
        operation_kind=WithholdingOperationKind.COMMON,
        calculation_base_brl=base,
        withholding_rate=_COMMON_WITHHOLDING_RATE,
        withholding_tax_brl=_money(base * _COMMON_WITHHOLDING_RATE),
    )


def assess_day_trade_withholding(
    *,
    competence_month: str,
    net_day_trade_result_brl: Decimal,
) -> FiscalWithholdingAssessment:
    """Calcula IRRF Day Trade somente sobre resultado líquido positivo."""

    base = _money(max(Decimal(0), net_day_trade_result_brl))
    return FiscalWithholdingAssessment(
        competence_month=competence_month,
        operation_kind=WithholdingOperationKind.DAY_TRADE,
        calculation_base_brl=base,
        withholding_rate=_DAY_TRADE_WITHHOLDING_RATE,
        withholding_tax_brl=_money(base * _DAY_TRADE_WITHHOLDING_RATE),
    )
