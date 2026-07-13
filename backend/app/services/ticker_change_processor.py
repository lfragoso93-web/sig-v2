"""Aplicacao idempotente de trocas de ticker em carteiras."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent, CorporateEventStatus, CorporateEventType
from app.models.transaction import OperationType, Transaction


_MARKER_PREFIX = "Evento corporativo - troca de ticker"


@dataclass(frozen=True)
class PositionAtEvent:
    quantity: float
    total_cost: float
    asset_type: str
    currency: str

    @property
    def average_price(self) -> float:
        return self.total_cost / self.quantity if self.quantity > 0 else 0.0


def _is_buy(operation: object) -> bool:
    return operation == OperationType.buy or str(operation).lower() == "buy"


def _is_sell(operation: object) -> bool:
    return operation == OperationType.sell or str(operation).lower() == "sell"


def calculate_position_at_event(transactions: Iterable[Transaction]) -> PositionAtEvent:
    quantity = 0.0
    total_cost = 0.0
    asset_type = "ACAO"
    currency = "BRL"

    for tx in transactions:
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        asset_type = str(tx.asset_type)
        currency = str(tx.currency or "BRL")

        if _is_buy(tx.operation):
            quantity += qty
            total_cost += qty * price + fees
        elif _is_sell(tx.operation) and quantity > 0:
            sold = min(qty, quantity)
            fraction = sold / quantity
            total_cost -= total_cost * fraction
            quantity -= sold

    if quantity <= 1e-9:
        quantity = 0.0
        total_cost = 0.0

    return PositionAtEvent(
        quantity=quantity,
        total_cost=total_cost,
        asset_type=asset_type,
        currency=currency,
    )


async def apply_ticker_change_event(
    db: AsyncSession,
    event: CorporateEvent,
) -> bool:
    if event.event_type != CorporateEventType.TICKER_CHANGE:
        return False
    if event.portfolio_id is None or not event.raw_data:
        return False

    payload = json.loads(event.raw_data)
    old_ticker = str(payload.get("old_ticker") or "").upper()
    new_ticker = str(payload.get("new_ticker") or "").upper()
    if not old_ticker or not new_ticker:
        return False

    marker = f"{_MARKER_PREFIX} #{event.id}"
    existing_result = await db.execute(
        select(Transaction.id).where(
            Transaction.portfolio_id == event.portfolio_id,
            Transaction.notes == marker,
        )
    )
    if existing_result.first() is not None:
        event.status = CorporateEventStatus.APLICADO
        event.applied_at = datetime.utcnow()
        return False

    tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == event.portfolio_id,
            Transaction.ticker == old_ticker,
            Transaction.date < event.event_date,
        )
        .order_by(Transaction.date, Transaction.id)
    )
    position = calculate_position_at_event(tx_result.scalars().all())

    if position.quantity <= 0:
        event.status = CorporateEventStatus.APLICADO
        event.applied_at = datetime.utcnow()
        await db.flush()
        return False

    common = {
        "portfolio_id": event.portfolio_id,
        "asset_type": position.asset_type,
        "quantity": position.quantity,
        "price": position.average_price,
        "fees": 0.0,
        "date": event.event_date,
        "currency": position.currency,
        "notes": marker,
    }
    db.add(Transaction(ticker=old_ticker, operation=OperationType.sell, **common))
    db.add(Transaction(ticker=new_ticker, operation=OperationType.buy, **common))

    event.status = CorporateEventStatus.APLICADO
    event.applied_at = datetime.utcnow()
    await db.flush()
    return True


async def apply_pending_ticker_changes(
    db: AsyncSession,
    portfolio_id: int,
) -> int:
    result = await db.execute(
        select(CorporateEvent).where(
            CorporateEvent.portfolio_id == portfolio_id,
            CorporateEvent.event_type == CorporateEventType.TICKER_CHANGE,
            CorporateEvent.status == CorporateEventStatus.PENDENTE,
        )
    )

    applied = 0
    for event in result.scalars().all():
        if await apply_ticker_change_event(db, event):
            applied += 1
    return applied
