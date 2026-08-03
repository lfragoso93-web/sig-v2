"""Adaptador fiscal read-only para baixas realizadas canônicas.

Este módulo não calcula posição, custo ou PnL. Ele apenas converte
``CanonicalRealizedDisposal`` em entradas mensais com política fiscal explícita
por classe, preservando a separação entre projeção financeira e tributação.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.irpf_tax_policy import (
    TaxAssessmentGroup,
    TaxClassPolicy,
    resolve_tax_policy,
)
from app.services.position_timeline_projection import CanonicalRealizedDisposal


@dataclass(frozen=True)
class FiscalRealizedEntry:
    """Entrada fiscal derivada de uma única baixa financeira canônica."""

    transaction_id: int | str | None
    ticker: str
    asset_type: str
    disposal_date: date
    competence_month: str
    quantity_requested: Decimal
    quantity_disposed: Decimal
    gross_proceeds_brl: Decimal
    cost_basis_brl: Decimal
    fees_brl: Decimal
    realized_pnl_brl: Decimal
    policy: TaxClassPolicy
    common_group: TaxAssessmentGroup


@dataclass(frozen=True)
class FiscalMonthlyGroup:
    """Agregação mensal por grupo fiscal, sem aplicar isenção ou compensação."""

    competence_month: str
    group: TaxAssessmentGroup
    gross_proceeds_brl: Decimal
    cost_basis_brl: Decimal
    fees_brl: Decimal
    realized_pnl_brl: Decimal
    entries: tuple[FiscalRealizedEntry, ...]


def adapt_realized_disposal(
    disposal: CanonicalRealizedDisposal,
) -> FiscalRealizedEntry:
    """Converte uma baixa canônica em entrada fiscal de operação comum."""

    policy = resolve_tax_policy(disposal.asset_type)
    return FiscalRealizedEntry(
        transaction_id=disposal.transaction_id,
        ticker=disposal.ticker,
        asset_type=policy.canonical_class,
        disposal_date=disposal.disposal_date,
        competence_month=disposal.disposal_date.strftime("%Y-%m"),
        quantity_requested=disposal.quantity_requested,
        quantity_disposed=disposal.quantity_disposed,
        gross_proceeds_brl=disposal.gross_proceeds_brl,
        cost_basis_brl=disposal.cost_basis_brl,
        fees_brl=disposal.fees_brl,
        realized_pnl_brl=disposal.realized_pnl_brl,
        policy=policy,
        common_group=policy.common_group,
    )


def adapt_realized_disposals(
    disposals: tuple[CanonicalRealizedDisposal, ...]
    | list[CanonicalRealizedDisposal],
) -> tuple[FiscalRealizedEntry, ...]:
    """Converte e ordena baixas canônicas sem alterar seus valores financeiros."""

    return tuple(
        sorted(
            (adapt_realized_disposal(disposal) for disposal in disposals),
            key=lambda item: (
                item.disposal_date,
                item.ticker,
                str(item.transaction_id or ""),
            ),
        )
    )


def group_common_entries_by_month(
    entries: tuple[FiscalRealizedEntry, ...] | list[FiscalRealizedEntry],
) -> tuple[FiscalMonthlyGroup, ...]:
    """Agrupa operações comuns por mês e grupo fiscal sem misturar classes."""

    grouped: dict[tuple[str, TaxAssessmentGroup], list[FiscalRealizedEntry]] = (
        defaultdict(list)
    )
    for entry in entries:
        grouped[(entry.competence_month, entry.common_group)].append(entry)

    result: list[FiscalMonthlyGroup] = []
    for (month, group), items in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1].value),
    ):
        result.append(
            FiscalMonthlyGroup(
                competence_month=month,
                group=group,
                gross_proceeds_brl=sum(
                    (item.gross_proceeds_brl for item in items),
                    start=Decimal(0),
                ),
                cost_basis_brl=sum(
                    (item.cost_basis_brl for item in items),
                    start=Decimal(0),
                ),
                fees_brl=sum(
                    (item.fees_brl for item in items),
                    start=Decimal(0),
                ),
                realized_pnl_brl=sum(
                    (item.realized_pnl_brl for item in items),
                    start=Decimal(0),
                ),
                entries=tuple(items),
            )
        )
    return tuple(result)
