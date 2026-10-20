"""Read model de eventos corporativos aplicados a um ativo da carteira."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.clock import SYSTEM_CLOCK, Clock
from app.models.corporate_event import CorporateEvent
from app.models.transaction import Transaction
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.corporate_action_engine import NormalizedCorporateAction
from app.services.position_timeline_projection import PositionTimelineProjection
from app.services.snapshot_position_projection import (
    project_transaction_timelines,
)

READ_PORTFOLIO_CORPORATE_LIFECYCLE = "portfolio:corporate-lifecycle:read"
_IGNORED_EVENT_STATUS = "IGNORADO"


def _normalized_text(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return str(raw or "").strip()


def _lifecycle_items(
    *,
    ticker: str,
    actions: Sequence[NormalizedCorporateAction],
    projection: PositionTimelineProjection,
    pending_only: bool = False,
) -> list[dict[str, Any]]:
    applied_ids = set(projection.applied_event_ids)
    cash_by_event = {
        item.source_event_id: item
        for item in projection.corporate_action_cash_flows
    }
    pending_fraction_by_event = {
        item.source_event_id: item
        for item in getattr(projection, "pending_corporate_action_fractions", ())
    }
    lifecycle: list[dict[str, Any]] = []
    for action in actions:
        if action.source_event_id not in applied_ids:
            continue
        cash_flow = cash_by_event.get(action.source_event_id)
        pending_fraction = pending_fraction_by_event.get(action.source_event_id)
        if pending_only and pending_fraction is None:
            continue
        lifecycle.append(
            {
                "source_event_id": action.source_event_id,
                "ticker": ticker,
                "event_date": action.event_date,
                "event_type": action.kind.value,
                "quantity_factor": action.quantity_factor,
                "fractional_quantity": (
                    cash_flow.fractional_quantity
                    if cash_flow
                    else (
                        pending_fraction.fractional_quantity
                        if pending_fraction
                        else None
                    )
                ),
                "settlement_status": (
                    "SETTLED"
                    if cash_flow
                    else ("PENDING_VALUE" if pending_fraction else None)
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
                    else (
                        "Fração pendente de liquidação; valor ainda não confirmado."
                        if pending_fraction
                        else None
                    )
                ),
            }
        )
    return lifecycle


async def load_portfolio_asset_corporate_lifecycle(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
    ticker: str,
    clock: Clock = SYSTEM_CLOCK,
) -> list[dict[str, Any]]:
    """Retorna apenas eventos reconciliados que afetaram a posição."""

    await get_accessible_portfolio(
        db,
        access,
        required_permission=READ_PORTFOLIO_CORPORATE_LIFECYCLE,
    )
    portfolio_id = access.portfolio_id
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
    return _lifecycle_items(
        ticker=normalized_ticker,
        actions=actions,
        projection=projection,
    )


async def load_portfolio_pending_corporate_fractions(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
    clock: Clock = SYSTEM_CLOCK,
) -> list[dict[str, Any]]:
    """Lista frações pendentes da carteira sem estimar seus valores."""
    await get_accessible_portfolio(
        db,
        access,
        required_permission=READ_PORTFOLIO_CORPORATE_LIFECYCLE,
    )
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == access.portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return []

    tickers = sorted({str(tx.ticker).strip().upper() for tx in transactions})
    actions_by_ticker = await load_global_corporate_actions_by_ticker(db, tickers)
    timelines = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=clock.today(),
    )
    pending = [
        item
        for ticker, actions in actions_by_ticker.items()
        for item in _lifecycle_items(
            ticker=ticker,
            actions=actions,
            projection=timelines[ticker][0],
            pending_only=True,
        )
    ]
    return sorted(pending, key=lambda item: (item["event_date"], item["ticker"]))


async def load_upcoming_portfolio_corporate_events(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
    clock: Clock = SYSTEM_CLOCK,
) -> list[dict[str, Any]]:
    """List confirmed future events for assets currently held by the portfolio."""

    await get_accessible_portfolio(
        db,
        access,
        required_permission=READ_PORTFOLIO_CORPORATE_LIFECYCLE,
    )
    portfolio_id = access.portfolio_id
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return []

    tickers = sorted({str(tx.ticker).strip().upper() for tx in transactions})
    actions_by_ticker = await load_global_corporate_actions_by_ticker(db, tickers)
    projections = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=clock.today(),
    )
    held_tickers = sorted(
        ticker
        for ticker, (projection, _asset_type, _is_usd) in projections.items()
        if projection.quantity > 0
    )
    if not held_tickers:
        return []

    events_result = await db.execute(
        select(CorporateEvent)
        .where(
            CorporateEvent.portfolio_id.is_(None),
            func.upper(func.trim(CorporateEvent.ticker)).in_(held_tickers),
            CorporateEvent.effective_date >= clock.today(),
            CorporateEvent.reconciliation_status == "MATCHED",
            CorporateEvent.is_canonical.is_(True),
            CorporateEvent.requires_review.is_(False),
            func.upper(func.trim(CorporateEvent.status)) != _IGNORED_EVENT_STATUS,
        )
        .order_by(CorporateEvent.effective_date, CorporateEvent.ticker, CorporateEvent.id)
    )
    return [
        {
            "event_id": int(event.id),
            "ticker": str(event.ticker).strip().upper(),
            "event_type": _normalized_text(event.event_type),
            "event_date": event.effective_date,
            "description": event.description,
        }
        for event in events_result.scalars().all()
    ]
