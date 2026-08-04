"""Comparação read-only entre a apuração canônica e o runtime fiscal legado.

O comparador não altera consumidores, schemas ou regras de produção. Ele executa
os dois caminhos e classifica divergências mensais para orientar a migração da
Issue #56 com evidência explícita.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.irpf_annual_common_assessment_service import (
    FiscalAnnualCommonAssessment,
    assess_annual_common_operations,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup
from app.services.irpf_tax_service import calc_ganhos_capital

_CENT = Decimal("0.01")


class FiscalComparisonKind(StrEnum):
    """Causas conhecidas ou neutras de divergência entre os dois motores."""

    MATCH = "match"
    LEGACY_MISSING_MONTH = "legacy_missing_month"
    CANONICAL_MISSING_MONTH = "canonical_missing_month"
    CLASS_SEGREGATION = "class_segregation"
    STOCK_EXEMPTION = "stock_exemption"
    LOSS_CARRYFORWARD = "loss_carryforward"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FiscalMonthlyComparison:
    competence_month: str
    canonical_realized_pnl_brl: Decimal
    legacy_realized_pnl_brl: Decimal
    canonical_taxable_base_brl: Decimal
    legacy_taxable_base_brl: Decimal
    canonical_tax_due_brl: Decimal
    legacy_tax_due_brl: Decimal
    kinds: tuple[FiscalComparisonKind, ...]
    canonical_groups: tuple[TaxAssessmentGroup, ...]

    @property
    def matches(self) -> bool:
        return self.kinds == (FiscalComparisonKind.MATCH,)


@dataclass(frozen=True)
class FiscalAnnualComparison:
    portfolio_id: int
    year: int
    monthly: tuple[FiscalMonthlyComparison, ...]

    @property
    def has_divergences(self) -> bool:
        return any(not item.matches for item in self.monthly)


def _money(value: Decimal | float) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _canonical_months(
    annual: FiscalAnnualCommonAssessment,
) -> dict[str, dict[str, object]]:
    months: dict[str, dict[str, object]] = {}
    for item in annual.monthly:
        bucket = months.setdefault(
            item.competence_month,
            {
                "realized": Decimal(0),
                "base": Decimal(0),
                "tax": Decimal(0),
                "groups": set(),
                "exemption": False,
                "loss_used": Decimal(0),
            },
        )
        bucket["realized"] += item.realized_pnl_brl
        bucket["base"] += item.taxable_base_brl
        bucket["tax"] += item.tax_due_brl
        bucket["groups"].add(item.group)
        bucket["exemption"] = bool(bucket["exemption"] or item.exemption_applied)
        bucket["loss_used"] += item.loss_used_brl
    return months


def _classify(
    *,
    canonical_present: bool,
    legacy_present: bool,
    groups: tuple[TaxAssessmentGroup, ...],
    exemption_applied: bool,
    loss_used_brl: Decimal,
    canonical_values: tuple[Decimal, Decimal, Decimal],
    legacy_values: tuple[Decimal, Decimal, Decimal],
) -> tuple[FiscalComparisonKind, ...]:
    if canonical_values == legacy_values and canonical_present == legacy_present:
        return (FiscalComparisonKind.MATCH,)

    kinds: list[FiscalComparisonKind] = []
    if canonical_present and not legacy_present:
        kinds.append(FiscalComparisonKind.LEGACY_MISSING_MONTH)
    if legacy_present and not canonical_present:
        kinds.append(FiscalComparisonKind.CANONICAL_MISSING_MONTH)
    if len(groups) > 1 or any(
        group is not TaxAssessmentGroup.STOCKS for group in groups
    ):
        kinds.append(FiscalComparisonKind.CLASS_SEGREGATION)
    if exemption_applied:
        kinds.append(FiscalComparisonKind.STOCK_EXEMPTION)
    if loss_used_brl > 0:
        kinds.append(FiscalComparisonKind.LOSS_CARRYFORWARD)
    if not kinds:
        kinds.append(FiscalComparisonKind.UNKNOWN)
    return tuple(dict.fromkeys(kinds))


def build_annual_comparison(
    *,
    portfolio_id: int,
    year: int,
    canonical: FiscalAnnualCommonAssessment,
    legacy_months: list,
) -> FiscalAnnualComparison:
    """Compara resultados mensais sem inferir equivalência entre classes."""

    canonical_by_month = _canonical_months(canonical)
    legacy_by_month = {item.mes: item for item in legacy_months}
    months = sorted(set(canonical_by_month) | set(legacy_by_month))
    result: list[FiscalMonthlyComparison] = []

    for month in months:
        canonical_item = canonical_by_month.get(month)
        legacy_item = legacy_by_month.get(month)
        groups = tuple(
            sorted(
                canonical_item["groups"] if canonical_item else set(),
                key=lambda item: item.value,
            )
        )
        canonical_values = (
            _money(canonical_item["realized"] if canonical_item else 0),
            _money(canonical_item["base"] if canonical_item else 0),
            _money(canonical_item["tax"] if canonical_item else 0),
        )
        legacy_values = (
            _money(legacy_item.lucro_swing_trade if legacy_item else 0),
            _money(legacy_item.base_calculo if legacy_item else 0),
            _money(legacy_item.ir_devido_swing if legacy_item else 0),
        )
        kinds = _classify(
            canonical_present=canonical_item is not None,
            legacy_present=legacy_item is not None,
            groups=groups,
            exemption_applied=bool(
                canonical_item and canonical_item["exemption"]
            ),
            loss_used_brl=_money(
                canonical_item["loss_used"] if canonical_item else 0
            ),
            canonical_values=canonical_values,
            legacy_values=legacy_values,
        )
        result.append(
            FiscalMonthlyComparison(
                competence_month=month,
                canonical_realized_pnl_brl=canonical_values[0],
                legacy_realized_pnl_brl=legacy_values[0],
                canonical_taxable_base_brl=canonical_values[1],
                legacy_taxable_base_brl=legacy_values[1],
                canonical_tax_due_brl=canonical_values[2],
                legacy_tax_due_brl=legacy_values[2],
                kinds=kinds,
                canonical_groups=groups,
            )
        )

    return FiscalAnnualComparison(
        portfolio_id=portfolio_id,
        year=year,
        monthly=tuple(result),
    )


async def compare_annual_common_with_legacy(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> FiscalAnnualComparison:
    """Executa os dois motores e devolve somente uma visão comparativa."""

    canonical = await assess_annual_common_operations(db, portfolio_id, year)
    legacy = await calc_ganhos_capital(db, portfolio_id, year)
    return build_annual_comparison(
        portfolio_id=portfolio_id,
        year=year,
        canonical=canonical,
        legacy_months=legacy,
    )
