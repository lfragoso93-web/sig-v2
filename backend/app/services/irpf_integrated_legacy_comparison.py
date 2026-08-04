"""Comparação mensal read-only entre apuração integrada canônica e legado IRPF."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.services.irpf_annual_integrated_assessment_service import (
    FiscalAnnualIntegratedAssessment,
)

_CENT = Decimal("0.01")


class IntegratedFiscalComparisonKind(StrEnum):
    MATCH = "match"
    LEGACY_MISSING_MONTH = "legacy_missing_month"
    CANONICAL_MISSING_MONTH = "canonical_missing_month"
    SWING_RESULT = "swing_result"
    SWING_TAXABLE_BASE = "swing_taxable_base"
    SWING_TAX_DUE = "swing_tax_due"
    DAY_TRADE_RESULT = "day_trade_result"
    DAY_TRADE_TAXABLE_BASE = "day_trade_taxable_base"
    DAY_TRADE_TAX_DUE = "day_trade_tax_due"
    LOSS_CARRYFORWARD = "loss_carryforward"


@dataclass(frozen=True)
class IntegratedFiscalMonthlyComparison:
    competence_month: str
    canonical_swing_result_brl: Decimal
    legacy_swing_result_brl: Decimal
    canonical_swing_taxable_base_brl: Decimal
    legacy_swing_taxable_base_brl: Decimal
    canonical_swing_tax_due_brl: Decimal
    legacy_swing_tax_due_brl: Decimal
    canonical_day_trade_result_brl: Decimal
    legacy_day_trade_result_brl: Decimal
    canonical_day_trade_taxable_base_brl: Decimal
    legacy_day_trade_taxable_base_brl: Decimal
    canonical_day_trade_tax_due_brl: Decimal
    legacy_day_trade_tax_due_brl: Decimal
    kinds: tuple[IntegratedFiscalComparisonKind, ...]

    @property
    def matches(self) -> bool:
        return self.kinds == (IntegratedFiscalComparisonKind.MATCH,)


@dataclass(frozen=True)
class IntegratedFiscalAnnualComparison:
    portfolio_id: int
    year: int
    monthly: tuple[IntegratedFiscalMonthlyComparison, ...]

    @property
    def has_divergences(self) -> bool:
        return any(not item.matches for item in self.monthly)


def _money(value: Decimal | float) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _canonical_months(
    assessment: FiscalAnnualIntegratedAssessment,
) -> dict[str, dict[str, Decimal]]:
    months: dict[str, dict[str, Decimal]] = {}
    for item in assessment.swing.monthly:
        bucket = months.setdefault(
            item.competence_month,
            {
                "swing_result": Decimal(0),
                "swing_base": Decimal(0),
                "swing_tax": Decimal(0),
                "day_trade_result": Decimal(0),
                "day_trade_base": Decimal(0),
                "day_trade_tax": Decimal(0),
                "loss_used": Decimal(0),
            },
        )
        bucket["swing_result"] += item.realized_pnl_brl
        bucket["swing_base"] += item.taxable_base_brl
        bucket["swing_tax"] += item.tax_due_brl
        bucket["loss_used"] += item.loss_used_brl

    for item in assessment.day_trade_monthly:
        bucket = months.setdefault(
            item.competence_month,
            {
                "swing_result": Decimal(0),
                "swing_base": Decimal(0),
                "swing_tax": Decimal(0),
                "day_trade_result": Decimal(0),
                "day_trade_base": Decimal(0),
                "day_trade_tax": Decimal(0),
                "loss_used": Decimal(0),
            },
        )
        bucket["day_trade_result"] += item.realized_pnl_brl
        bucket["day_trade_base"] += item.taxable_base_brl
        bucket["day_trade_tax"] += item.tax_due_brl
        bucket["loss_used"] += item.loss_used_brl
    return months


def _legacy_value(item: object | None, name: str) -> Decimal:
    return _money(getattr(item, name, 0) if item is not None else 0)


def build_integrated_annual_comparison(
    *,
    portfolio_id: int,
    year: int,
    canonical: FiscalAnnualIntegratedAssessment,
    legacy_months: list,
) -> IntegratedFiscalAnnualComparison:
    canonical_by_month = _canonical_months(canonical)
    legacy_by_month = {item.mes: item for item in legacy_months}
    months = sorted(set(canonical_by_month) | set(legacy_by_month))
    result: list[IntegratedFiscalMonthlyComparison] = []

    for month in months:
        canonical_item = canonical_by_month.get(month)
        legacy_item = legacy_by_month.get(month)
        canonical_values = {
            key: _money(canonical_item[key] if canonical_item else 0)
            for key in (
                "swing_result",
                "swing_base",
                "swing_tax",
                "day_trade_result",
                "day_trade_base",
                "day_trade_tax",
            )
        }
        legacy_values = {
            "swing_result": _legacy_value(legacy_item, "lucro_swing_trade"),
            "swing_base": _legacy_value(legacy_item, "base_calculo"),
            "swing_tax": _legacy_value(legacy_item, "ir_devido_swing"),
            "day_trade_result": _legacy_value(legacy_item, "lucro_day_trade"),
            "day_trade_base": _legacy_value(legacy_item, "lucro_day_trade"),
            "day_trade_tax": _legacy_value(legacy_item, "ir_devido_day_trade"),
        }

        kinds: list[IntegratedFiscalComparisonKind] = []
        if canonical_item is not None and legacy_item is None:
            kinds.append(IntegratedFiscalComparisonKind.LEGACY_MISSING_MONTH)
        if legacy_item is not None and canonical_item is None:
            kinds.append(IntegratedFiscalComparisonKind.CANONICAL_MISSING_MONTH)
        comparisons = (
            ("swing_result", IntegratedFiscalComparisonKind.SWING_RESULT),
            ("swing_base", IntegratedFiscalComparisonKind.SWING_TAXABLE_BASE),
            ("swing_tax", IntegratedFiscalComparisonKind.SWING_TAX_DUE),
            ("day_trade_result", IntegratedFiscalComparisonKind.DAY_TRADE_RESULT),
            (
                "day_trade_base",
                IntegratedFiscalComparisonKind.DAY_TRADE_TAXABLE_BASE,
            ),
            ("day_trade_tax", IntegratedFiscalComparisonKind.DAY_TRADE_TAX_DUE),
        )
        for key, kind in comparisons:
            if canonical_values[key] != legacy_values[key]:
                kinds.append(kind)
        if canonical_item and _money(canonical_item["loss_used"]) > 0:
            kinds.append(IntegratedFiscalComparisonKind.LOSS_CARRYFORWARD)
        if not kinds:
            kinds.append(IntegratedFiscalComparisonKind.MATCH)

        result.append(
            IntegratedFiscalMonthlyComparison(
                competence_month=month,
                canonical_swing_result_brl=canonical_values["swing_result"],
                legacy_swing_result_brl=legacy_values["swing_result"],
                canonical_swing_taxable_base_brl=canonical_values["swing_base"],
                legacy_swing_taxable_base_brl=legacy_values["swing_base"],
                canonical_swing_tax_due_brl=canonical_values["swing_tax"],
                legacy_swing_tax_due_brl=legacy_values["swing_tax"],
                canonical_day_trade_result_brl=canonical_values["day_trade_result"],
                legacy_day_trade_result_brl=legacy_values["day_trade_result"],
                canonical_day_trade_taxable_base_brl=canonical_values[
                    "day_trade_base"
                ],
                legacy_day_trade_taxable_base_brl=legacy_values["day_trade_base"],
                canonical_day_trade_tax_due_brl=canonical_values["day_trade_tax"],
                legacy_day_trade_tax_due_brl=legacy_values["day_trade_tax"],
                kinds=tuple(dict.fromkeys(kinds)),
            )
        )

    return IntegratedFiscalAnnualComparison(
        portfolio_id=portfolio_id,
        year=year,
        monthly=tuple(result),
    )
