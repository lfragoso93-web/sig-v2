"""Projeção cronológica pura de transações e eventos corporativos."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)


class PositionMovementKind(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class PositionMovement:
    movement_date: date
    kind: PositionMovementKind
    quantity: Decimal
    unit_price: Decimal
    fees: Decimal = Decimal(0)
    total_cost_original_currency: Decimal = Decimal(0)


@dataclass(frozen=True)
class PositionTimelineProjection:
    quantity: Decimal
    total_cost: Decimal
    total_cost_original_currency: Decimal
    realized_pnl: Decimal
    applied_event_ids: tuple[str, ...]
    subscription_event_ids: tuple[str, ...]

    @property
    def average_price(self) -> Decimal:
        if self.quantity <= 0:
            return Decimal(0)
        return self.total_cost / self.quantity

    @property
    def average_price_original_currency(self) -> Decimal | None:
        if self.quantity <= 0 or self.total_cost_original_currency <= 0:
            return None
        return self.total_cost_original_currency / self.quantity


def project_position_timeline(
    *,
    movements: Iterable[PositionMovement],
    actions: Iterable[NormalizedCorporateAction],
    through_date: date | None = None,
) -> PositionTimelineProjection:
    """Intercala operações e eventos sem alterar o histórico persistido.

    Operações são processadas antes de eventos na mesma data. Assim, uma compra
    registrada na data efetiva participa do evento; uma venda na mesma data reduz
    primeiro a quantidade elegível. Essa convenção é explícita e poderá ser
    refinada por tipo de evento quando houver datas de direito distintas.
    """

    quantity = Decimal(0)
    total_cost = Decimal(0)
    total_cost_original_currency = Decimal(0)
    realized_pnl = Decimal(0)
    applied: list[str] = []
    subscriptions: list[str] = []

    timeline: list[tuple[date, int, str, object]] = []
    for index, movement in enumerate(movements):
        if movement.quantity < 0 or movement.unit_price < 0 or movement.fees < 0:
            raise ValueError("movimentos não aceitam valores negativos")
        timeline.append((movement.movement_date, 0, f"movement:{index}", movement))
    for action in actions:
        timeline.append((action.event_date, 1, action.source_event_id, action))

    for item_date, _, _, item in sorted(timeline, key=lambda value: value[:3]):
        if through_date is not None and item_date > through_date:
            continue

        if isinstance(item, PositionMovement):
            if item.kind == PositionMovementKind.BUY:
                quantity += item.quantity
                total_cost += item.quantity * item.unit_price + item.fees
                total_cost_original_currency += item.total_cost_original_currency
                continue

            if item.kind == PositionMovementKind.SELL and quantity > 0:
                sold = min(item.quantity, quantity)
                average_price = total_cost / quantity
                realized_pnl += sold * (item.unit_price - average_price) - item.fees
                ratio = sold / quantity
                total_cost -= total_cost * ratio
                total_cost_original_currency -= total_cost_original_currency * ratio
                quantity -= sold
                if quantity == 0:
                    total_cost = Decimal(0)
                    total_cost_original_currency = Decimal(0)
                continue

        action = item
        if action.kind == CorporateActionKind.SUBSCRIPTION:
            if quantity > 0:
                subscriptions.append(action.source_event_id)
            continue
        if quantity <= 0:
            continue
        quantity *= action.quantity_factor
        applied.append(action.source_event_id)

    return PositionTimelineProjection(
        quantity=quantity,
        total_cost=total_cost,
        total_cost_original_currency=total_cost_original_currency,
        realized_pnl=realized_pnl,
        applied_event_ids=tuple(applied),
        subscription_event_ids=tuple(subscriptions),
    )
