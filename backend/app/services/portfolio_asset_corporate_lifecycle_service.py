"""Read model de eventos corporativos aplicados a um ativo da carteira."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SYSTEM_CLOCK, Clock
from app.models.transaction import Transaction
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.snapshot_position_projection import (
    project_transaction_timelines,
)


async def load_portfolio_asset_corporate_lifecycle(
    db: AsyncSession,
    *,
    portfolio_id: int,
    ticker: str,
    clock: Clock = SYSTEM_CLOCK,
) -> list[dict[str, Any]]:
    """Retorna apenas eventos reconciliados que afetaram a posição."""

    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker e obrigatorio")

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            func.upper(func.trim(Transaction.ticker)) == normalized_ticker,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return []

    actions_by_ticker = await load_global_corporate_actions_by_ticker(
        db,
        [normalized_ticker],
    )
    actions = actions_by_ticker.get(normalized_ticker, ())
    timelines = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=clock.today(),
    )
    projection = timelines[normalized_ticker][0]
    applied_ids = set(projection.applied_event_ids)
    cash_by_event = {
        item.source_event_id: item
        for item in projection.corporate_action_cash_flows
    }

    lifecycle: list[dict[str, Any]] = []
    for action in actions:
        if action.source_event_id not in applied_ids:
            continue
        cash_flow = cash_by_event.get(action.source_event_id)
        lifecycle.append(
            {
                "source_event_id": action.source_event_id,
                "ticker": normalized_ticker,
                "event_date": action.event_date,
                "event_type": action.kind.value,
                "quantity_factor": action.quantity_factor,
                "fractional_quantity": (
                    cash_flow.fractional_quantity if cash_flow else None
                ),
                "unit_settlement_price_brl": (
                    cash_flow.unit_settlement_price_brl if cash_flow else None
                ),
                "gross_amount_brl": (
                    cash_flow.gross_amount_brl if cash_flow else None
                ),
                "cost_basis_brl": (
                    cash_flow.cost_basis_brl if cash_flow else None
                ),
                "realized_pnl_brl": (
                    cash_flow.realized_pnl_brl if cash_flow else None
                ),
                "cash_treatment": (
                    cash_flow.cash_treatment if cash_flow else None
                ),
                "message": (
                    "Fração vendida e valor creditado ao usuário."
                    if cash_flow
                    else None
                ),
            }
        )

    return lifecycle
