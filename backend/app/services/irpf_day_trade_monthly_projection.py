"""Projeção mensal quantitativa de Day Trade e excedentes Swing Trade."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.services.irpf_day_trade_matcher import (
    DayTradeMatch,
    FiscalTradeOperation,
    match_day_trades,
)


@dataclass(frozen=True)
class DayTradeMonthlyProjection:
    competence_month: str
    matched_quantity: Decimal
    day_trade_result_brl: Decimal
    unmatched_buy_quantity: Decimal
    unmatched_sell_quantity: Decimal
    matches: tuple[DayTradeMatch, ...]


def project_day_trades_by_month(
    operations: Iterable[FiscalTradeOperation],
) -> tuple[DayTradeMonthlyProjection, ...]:
    """Consolida matches e excedentes por competência mensal."""

    ordered = tuple(operations)
    result = match_day_trades(ordered)
    operation_by_id = {item.transaction_id: item for item in ordered}

    matches_by_month: dict[str, list[DayTradeMatch]] = {}
    for match in result.matches:
        competence = match.trade_date.strftime("%Y-%m")
        matches_by_month.setdefault(competence, []).append(match)

    unmatched_buys: dict[str, Decimal] = {}
    unmatched_sells: dict[str, Decimal] = {}
    for transaction_id, quantity in result.unmatched_quantities.items():
        if quantity == 0:
            continue
        operation = operation_by_id[transaction_id]
        competence = operation.trade_date.strftime("%Y-%m")
        target = unmatched_buys if operation.operation.value == "buy" else unmatched_sells
        target[competence] = target.get(competence, Decimal(0)) + quantity

    competences = sorted(
        set(matches_by_month) | set(unmatched_buys) | set(unmatched_sells)
    )
    return tuple(
        DayTradeMonthlyProjection(
            competence_month=competence,
            matched_quantity=sum(
                (match.quantity for match in matches_by_month.get(competence, [])),
                Decimal(0),
            ),
            day_trade_result_brl=sum(
                (
                    match.gross_result_brl
                    for match in matches_by_month.get(competence, [])
                ),
                Decimal(0),
            ),
            unmatched_buy_quantity=unmatched_buys.get(competence, Decimal(0)),
            unmatched_sell_quantity=unmatched_sells.get(competence, Decimal(0)),
            matches=tuple(matches_by_month.get(competence, [])),
        )
        for competence in competences
    )
