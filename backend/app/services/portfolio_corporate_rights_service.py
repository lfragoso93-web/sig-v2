"""Portfolio-scoped, read-only projection of component fractional cash rights."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.clock import SYSTEM_CLOCK, Clock
from app.models.corporate_event import CorporateEvent
from app.models.corporate_event_reconciliation_evidence import (
    CorporateEventReconciliationEvidence,
)
from app.models.transaction import Transaction
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.services.corporate_action_fractional_entitlement import (
    derive_component_fractional_cash_entitlement,
)
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.snapshot_position_projection import project_transaction_timelines


def _source_event_id(event: CorporateEvent) -> str:
    source = str(event.source_provider or "catalog")
    source_id = str(
        event.source_event_id
        or event.brapi_event_id
        or f"corporate-event:{event.id}"
    )
    return f"{source}:{source_id}"


def _event_payload(event: CorporateEvent) -> dict[str, Any]:
    if isinstance(event.raw_metadata, dict):
        return event.raw_metadata
    if not event.raw_data:
        return {}
    try:
        parsed = json.loads(event.raw_data)
    except (TypeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    provider_payload = parsed.get("provider_payload")
    return provider_payload if isinstance(provider_payload, dict) else parsed


def _component_settlement(event: CorporateEvent) -> dict[str, Any] | None:
    payload = _event_payload(event)
    settlement = payload.get("fractional_component_settlement")
    if not isinstance(settlement, dict):
        return None
    if settlement.get("model") != "COMPONENT_BONUS_FRACTIONS_V1":
        return None
    if not str(settlement.get("evidence_reference", "")).strip():
        return None
    if not str(settlement.get("cash_treatment", "")).strip():
        return None
    try:
        cost_per_share = Decimal(str(settlement["bonus_cost_per_share_brl"]))
    except (KeyError, ArithmeticError, TypeError, ValueError):
        return None
    if not cost_per_share.is_finite() or cost_per_share < 0:
        return None
    return settlement


async def load_portfolio_corporate_rights(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
    clock: Clock = SYSTEM_CLOCK,
) -> list[dict[str, Any]]:
    """Calculate evidenced component fractions from holdings at each record date."""

    await get_accessible_portfolio(
        db,
        access,
        required_permission="portfolio:corporate-lifecycle:read",
    )
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == access.portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(tx_result.scalars().all())
    if not transactions:
        return []
    tickers = sorted({str(tx.ticker).strip().upper() for tx in transactions})

    event_result = await db.execute(
        select(CorporateEvent, CorporateEventReconciliationEvidence)
        .join(
            CorporateEventReconciliationEvidence,
            CorporateEventReconciliationEvidence.corporate_event_id
            == CorporateEvent.id,
        )
        .where(
            CorporateEvent.portfolio_id.is_(None),
            func.upper(func.trim(CorporateEvent.ticker)).in_(tickers),
            CorporateEvent.reconciliation_status == "MATCHED",
            CorporateEvent.is_canonical.is_(True),
            CorporateEvent.requires_review.is_(False),
            func.upper(func.trim(CorporateEvent.status)) != "IGNORADO",
            CorporateEventReconciliationEvidence.decision == "MATCHED",
            CorporateEvent.record_date.is_not(None),
            CorporateEvent.payment_date.is_not(None),
            CorporateEvent.effective_date.is_not(None),
        )
        .order_by(CorporateEvent.record_date, CorporateEvent.ticker, CorporateEvent.id)
    )
    events = list(event_result.all())
    configured_events = []
    for event, evidence in events:
        settlement = _component_settlement(event)
        if (
            settlement is not None
            and str(evidence.evidence_type).upper()
            in {"OFFICIAL_ISSUER_DOCUMENT", "OFFICIAL_EXCHANGE_DOCUMENT"}
            and str(settlement.get("evidence_reference", "")).strip()
            == str(evidence.evidence_reference or "").strip()
        ):
            configured_events.append((event, settlement))
    if not configured_events:
        return []

    actions_by_ticker = await load_global_corporate_actions_by_ticker(db, tickers)
    output: list[dict[str, Any]] = []
    for event, settlement in configured_events:
        assert settlement is not None
        if str(event.event_type).strip().upper() != "BONIFICACAO":
            continue
        record_date: date = event.record_date
        ticker = str(event.ticker).strip().upper()
        basis_transactions = [
            tx for tx in transactions
            if str(tx.ticker).strip().upper() == ticker and tx.date <= record_date
        ]
        if not basis_transactions:
            continue

        event_source_id = _source_event_id(event)
        prior_actions = tuple(
            action
            for action in actions_by_ticker.get(ticker, ())
            if action.source_event_id != event_source_id
        )
        projection_rows = project_transaction_timelines(
            transactions=basis_transactions,
            actions_by_ticker={ticker: prior_actions},
            target_date=record_date,
        )
        projected = projection_rows.get(ticker)
        if projected is None:
            continue
        base_position = Decimal(str(projected[0].quantity))
        if base_position <= 0:
            continue

        try:
            bonus_factor = Decimal(str(settlement["bonus_factor"]))
            components = settlement["components"]
            if not isinstance(components, list):
                continue
            unit_composition = settlement.get("unit_composition")
            if settlement.get("requires_unit_grouping") is True and not isinstance(
                unit_composition, dict
            ):
                continue
            entitlements = derive_component_fractional_cash_entitlement(
                base_position=base_position,
                bonus_factor=bonus_factor,
                components=components,
                unit_composition=unit_composition,
            )
        except (KeyError, TypeError, ValueError, ArithmeticError):
            # Incomplete or malformed event evidence remains outside this read model.
            continue

        fractional_components = [
            item for item in entitlements if item.fractional_quantity > 0
        ]
        gross_amount = sum(
            (item.gross_amount_brl for item in fractional_components),
            start=Decimal(0),
        )
        bonus_cost_per_share = Decimal(
            str(settlement["bonus_cost_per_share_brl"])
        )
        attributed_bonus_cost = sum(
            (item.bonus_quantity * bonus_cost_per_share for item in entitlements),
            start=Decimal(0),
        )
        fractional_cost_basis = sum(
            (
                item.fractional_quantity * bonus_cost_per_share
                for item in fractional_components
            ),
            start=Decimal(0),
        )
        component_payloads = []
        for item in entitlements:
            payload = item.to_dict()
            payload["attributed_cost_brl"] = (
                item.bonus_quantity * bonus_cost_per_share
            )
            payload["fractional_cost_basis_brl"] = (
                item.fractional_quantity * bonus_cost_per_share
            )
            payload["estimated_fractional_result_brl"] = (
                item.gross_amount_brl
                - item.fractional_quantity * bonus_cost_per_share
            )
            component_payloads.append(payload)
        output.append(
            {
                "event_id": int(event.id),
                "source_event_id": event_source_id,
                "ticker": ticker,
                "event_type": str(event.event_type),
                "record_date": record_date,
                "settlement_date": event.payment_date,
                "base_position": base_position,
                "settlement_status": (
                    "AVAILABLE"
                    if event.payment_date <= clock.today()
                    else "PENDING"
                ),
                "components": component_payloads,
                "gross_amount_brl": gross_amount,
                "calculated_gross_amount_brl": gross_amount,
                "bonus_cost_per_share_brl": bonus_cost_per_share,
                "attributed_bonus_cost_brl": attributed_bonus_cost,
                "fractional_cost_basis_brl": fractional_cost_basis,
                "estimated_fractional_result_brl": gross_amount
                - fractional_cost_basis,
                "cash_status": "CALCULATED_NOT_CONFIRMED",
                "cash_treatment": str(settlement.get("cash_treatment", "")),
                "evidence_reference": str(settlement["evidence_reference"]),
            }
        )
    return sorted(output, key=lambda item: (item["settlement_date"], item["ticker"]))
