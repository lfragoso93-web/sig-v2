"""Projeta excedentes Swing a partir de baixas canônicas e matches Day Trade.

O módulo é puro e read-only. Ele não recalcula custo médio: reduz cada baixa
canônica apenas pela quantidade intradiária já casada na mesma transação de
venda, preservando valores financeiros proporcionalmente.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from decimal import Decimal

from app.services.irpf_day_trade_matcher import DayTradeMatch
from app.services.position_timeline_projection import CanonicalRealizedDisposal


def _matched_sell_quantity_by_transaction(
    matches: tuple[DayTradeMatch, ...] | list[DayTradeMatch],
) -> dict[int | str, Decimal]:
    quantities: dict[int | str, Decimal] = defaultdict(Decimal)
    for match in matches:
        quantities[match.sell_transaction_id] += match.quantity
    return dict(quantities)


def project_swing_remainder_disposals(
    disposals: tuple[CanonicalRealizedDisposal, ...]
    | list[CanonicalRealizedDisposal],
    matches: tuple[DayTradeMatch, ...] | list[DayTradeMatch],
) -> tuple[CanonicalRealizedDisposal, ...]:
    """Remove quantitativamente a parcela Day Trade das baixas canônicas.

    Baixas sem ``transaction_id`` são preservadas, pois não podem ser vinculadas
    com segurança ao matcher. Se a quantidade intradiária consumir toda a baixa,
    ela é omitida da visão Swing. Excedentes parciais recebem rateio proporcional
    de proventos, custo, taxas, PnL e valor na moeda original.
    """

    matched_by_sell = _matched_sell_quantity_by_transaction(matches)
    result: list[CanonicalRealizedDisposal] = []

    for disposal in disposals:
        transaction_id = disposal.transaction_id
        if transaction_id is None:
            result.append(disposal)
            continue

        matched_quantity = matched_by_sell.get(transaction_id, Decimal(0))
        swing_quantity = max(Decimal(0), disposal.quantity_disposed - matched_quantity)
        if swing_quantity == 0:
            continue
        if swing_quantity == disposal.quantity_disposed:
            result.append(disposal)
            continue

        ratio = swing_quantity / disposal.quantity_disposed
        result.append(
            replace(
                disposal,
                quantity_requested=swing_quantity,
                quantity_disposed=swing_quantity,
                gross_proceeds_brl=disposal.gross_proceeds_brl * ratio,
                cost_basis_brl=disposal.cost_basis_brl * ratio,
                fees_brl=disposal.fees_brl * ratio,
                realized_pnl_brl=disposal.realized_pnl_brl * ratio,
                gross_proceeds_original_currency=(
                    disposal.gross_proceeds_original_currency * ratio
                    if disposal.gross_proceeds_original_currency is not None
                    else None
                ),
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.disposal_date,
                item.ticker,
                str(item.transaction_id or ""),
            ),
        )
    )
