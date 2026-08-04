"""Descoberta e comparação read-only de carteiras/anos com vendas realizadas."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.services.irpf_legacy_comparison_service import (
    FiscalAnnualComparison,
    FiscalComparisonKind,
    compare_annual_common_with_legacy,
)


@dataclass(frozen=True)
class FiscalComparisonTarget:
    portfolio_id: int
    year: int
    sale_count: int
    first_sale_date: date
    last_sale_date: date


@dataclass(frozen=True)
class FiscalComparisonBatchReport:
    targets: tuple[FiscalComparisonTarget, ...]
    comparisons: tuple[FiscalAnnualComparison, ...]
    months_compared: int
    matching_months: int
    divergent_months: int
    divergence_counts: dict[FiscalComparisonKind, int]


async def discover_comparison_targets(
    db: AsyncSession,
    *,
    start_year: int | None = None,
    end_year: int | None = None,
) -> tuple[FiscalComparisonTarget, ...]:
    """Localiza carteiras e anos com ao menos uma venda registrada."""

    if start_year is not None and start_year < 1900:
        raise ValueError("start_year inválido")
    if end_year is not None and end_year > 9999:
        raise ValueError("end_year inválido")
    if start_year is not None and end_year is not None and end_year < start_year:
        raise ValueError("end_year deve ser igual ou posterior a start_year")

    year_expr = extract("year", Transaction.date)
    statement = (
        select(
            Transaction.portfolio_id,
            year_expr.label("year"),
            Transaction.id,
            Transaction.date,
        )
        .where(Transaction.operation == OperationType.sell)
        .order_by(
            Transaction.portfolio_id.asc(),
            year_expr.asc(),
            Transaction.date.asc(),
            Transaction.id.asc(),
        )
    )
    if start_year is not None:
        statement = statement.where(year_expr >= start_year)
    if end_year is not None:
        statement = statement.where(year_expr <= end_year)

    rows = (await db.execute(statement)).all()
    grouped: dict[tuple[int, int], list[date]] = {}
    for portfolio_id, year, _transaction_id, sale_date in rows:
        grouped.setdefault((int(portfolio_id), int(year)), []).append(sale_date)

    return tuple(
        FiscalComparisonTarget(
            portfolio_id=portfolio_id,
            year=year,
            sale_count=len(dates),
            first_sale_date=min(dates),
            last_sale_date=max(dates),
        )
        for (portfolio_id, year), dates in sorted(grouped.items())
    )


def build_batch_report(
    *,
    targets: tuple[FiscalComparisonTarget, ...] | list[FiscalComparisonTarget],
    comparisons: tuple[FiscalAnnualComparison, ...]
    | list[FiscalAnnualComparison],
) -> FiscalComparisonBatchReport:
    """Agrega resultados sem ocultar causas de divergência."""

    ordered_targets = tuple(sorted(targets, key=lambda item: (item.portfolio_id, item.year)))
    ordered_comparisons = tuple(
        sorted(comparisons, key=lambda item: (item.portfolio_id, item.year))
    )
    counts: Counter[FiscalComparisonKind] = Counter()
    matching_months = 0
    divergent_months = 0

    for comparison in ordered_comparisons:
        for month in comparison.monthly:
            if month.matches:
                matching_months += 1
            else:
                divergent_months += 1
                counts.update(month.kinds)

    return FiscalComparisonBatchReport(
        targets=ordered_targets,
        comparisons=ordered_comparisons,
        months_compared=matching_months + divergent_months,
        matching_months=matching_months,
        divergent_months=divergent_months,
        divergence_counts=dict(sorted(counts.items(), key=lambda item: item[0].value)),
    )


async def compare_discovered_targets(
    db: AsyncSession,
    *,
    start_year: int | None = None,
    end_year: int | None = None,
) -> FiscalComparisonBatchReport:
    """Executa o comparador para todos os alvos encontrados na mesma sessão."""

    targets = await discover_comparison_targets(
        db,
        start_year=start_year,
        end_year=end_year,
    )
    comparisons = [
        await compare_annual_common_with_legacy(db, target.portfolio_id, target.year)
        for target in targets
    ]
    return build_batch_report(targets=targets, comparisons=comparisons)
