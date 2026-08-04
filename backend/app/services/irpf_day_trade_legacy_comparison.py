"""Comparação read-only entre a projeção quantitativa e o Day Trade legado."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Iterable

from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection


class DayTradeDivergenceKind(StrEnum):
    MATCH = "match"
    LEGACY_MISSING_MONTH = "legacy_missing_month"
    CANONICAL_MISSING_MONTH = "canonical_missing_month"
    QUANTITY = "day_trade_quantity"
    RESULT = "day_trade_result"


@dataclass(frozen=True)
class LegacyDayTradeMonth:
    competence_month: str
    matched_quantity: Decimal
    day_trade_result_brl: Decimal


@dataclass(frozen=True)
class DayTradeMonthComparison:
    competence_month: str
    canonical_matched_quantity: Decimal
    legacy_matched_quantity: Decimal
    canonical_result_brl: Decimal
    legacy_result_brl: Decimal
    quantity_delta: Decimal
    result_delta_brl: Decimal
    kinds: tuple[DayTradeDivergenceKind, ...]

    @property
    def is_match(self) -> bool:
        return self.kinds == (DayTradeDivergenceKind.MATCH,)


def compare_day_trade_months(
    canonical: Iterable[DayTradeMonthlyProjection],
    legacy: Iterable[LegacyDayTradeMonth],
) -> tuple[DayTradeMonthComparison, ...]:
    """Compara quantitativamente competências Day Trade sem alterar o runtime."""

    canonical_by_month = {item.competence_month: item for item in canonical}
    legacy_by_month = {item.competence_month: item for item in legacy}
    competences = sorted(set(canonical_by_month) | set(legacy_by_month))

    comparisons: list[DayTradeMonthComparison] = []
    for competence in competences:
        canonical_item = canonical_by_month.get(competence)
        legacy_item = legacy_by_month.get(competence)

        canonical_quantity = (
            canonical_item.matched_quantity if canonical_item else Decimal(0)
        )
        legacy_quantity = legacy_item.matched_quantity if legacy_item else Decimal(0)
        canonical_result = (
            canonical_item.day_trade_result_brl if canonical_item else Decimal(0)
        )
        legacy_result = legacy_item.day_trade_result_brl if legacy_item else Decimal(0)

        kinds: list[DayTradeDivergenceKind] = []
        if canonical_item is None:
            kinds.append(DayTradeDivergenceKind.CANONICAL_MISSING_MONTH)
        if legacy_item is None:
            kinds.append(DayTradeDivergenceKind.LEGACY_MISSING_MONTH)
        if canonical_quantity != legacy_quantity:
            kinds.append(DayTradeDivergenceKind.QUANTITY)
        if canonical_result != legacy_result:
            kinds.append(DayTradeDivergenceKind.RESULT)
        if not kinds:
            kinds.append(DayTradeDivergenceKind.MATCH)

        comparisons.append(
            DayTradeMonthComparison(
                competence_month=competence,
                canonical_matched_quantity=canonical_quantity,
                legacy_matched_quantity=legacy_quantity,
                canonical_result_brl=canonical_result,
                legacy_result_brl=legacy_result,
                quantity_delta=canonical_quantity - legacy_quantity,
                result_delta_brl=canonical_result - legacy_result,
                kinds=tuple(kinds),
            )
        )

    return tuple(comparisons)
