"""Projeção cronológica pura de transações e eventos corporativos."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import cast

from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.corporate_event_fractional_resolution import (
    FractionalResolutionPolicy,
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
    transaction_id: int | str | None = None
    ticker: str = ""
    asset_type: str = ""
    currency: str = "BRL"
    unit_price_original_currency: Decimal | None = None


@dataclass(frozen=True)
class CanonicalRealizedDisposal:
    """Baixa financeira auditável, sem classificação ou regra fiscal."""

    transaction_id: int | str | None
    ticker: str
    asset_type: str
    disposal_date: date
    quantity_requested: Decimal
    quantity_disposed: Decimal
    unit_proceeds_brl: Decimal
    gross_proceeds_brl: Decimal
    cost_basis_brl: Decimal
    fees_brl: Decimal
    realized_pnl_brl: Decimal
    currency: str
    gross_proceeds_original_currency: Decimal | None
    applied_event_ids: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalCorporateActionCashFlow:
    """Fluxo financeiro derivado de evento corporativo, fora do ledger."""

    source_event_id: str
    event_date: date
    fractional_quantity: Decimal
    unit_settlement_price_brl: Decimal
    gross_amount_brl: Decimal
    cash_treatment: str
    cost_basis_brl: Decimal = Decimal(0)
    realized_pnl_brl: Decimal = Decimal(0)


@dataclass(frozen=True)
class PendingCorporateActionFraction:
    """Known fractional quantity with settlement value not yet evidenced."""

    source_event_id: str
    event_date: date
    fractional_quantity: Decimal
    cost_basis_brl: Decimal = Decimal(0)
    cost_basis_original_currency: Decimal = Decimal(0)


@dataclass(frozen=True)
class PositionTimelineProjection:
    quantity: Decimal
    total_cost: Decimal
    total_cost_original_currency: Decimal
    realized_pnl: Decimal
    applied_event_ids: tuple[str, ...]
    subscription_event_ids: tuple[str, ...]
    realized_disposals: tuple[CanonicalRealizedDisposal, ...] = ()
    corporate_action_cash_flows: tuple[
        CanonicalCorporateActionCashFlow, ...
    ] = ()
    pending_corporate_action_fractions: tuple[
        PendingCorporateActionFraction, ...
    ] = ()

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
    disposals: list[CanonicalRealizedDisposal] = []
    corporate_action_cash_flows: list[CanonicalCorporateActionCashFlow] = []
    pending_corporate_action_fractions: list[PendingCorporateActionFraction] = []

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
                cost_basis = sold * average_price
                gross_proceeds = sold * item.unit_price
                disposal_pnl = gross_proceeds - cost_basis - item.fees
                realized_pnl += disposal_pnl
                original_proceeds = (
                    sold * item.unit_price_original_currency
                    if item.unit_price_original_currency is not None
                    else None
                )
                disposals.append(
                    CanonicalRealizedDisposal(
                        transaction_id=item.transaction_id,
                        ticker=item.ticker,
                        asset_type=item.asset_type,
                        disposal_date=item.movement_date,
                        quantity_requested=item.quantity,
                        quantity_disposed=sold,
                        unit_proceeds_brl=item.unit_price,
                        gross_proceeds_brl=gross_proceeds,
                        cost_basis_brl=cost_basis,
                        fees_brl=item.fees,
                        realized_pnl_brl=disposal_pnl,
                        currency=item.currency,
                        gross_proceeds_original_currency=original_proceeds,
                        applied_event_ids=tuple(applied),
                    )
                )
                ratio = sold / quantity
                total_cost -= total_cost * ratio
                total_cost_original_currency -= total_cost_original_currency * ratio
                quantity -= sold
                if quantity == 0:
                    total_cost = Decimal(0)
                    total_cost_original_currency = Decimal(0)
                continue

        action = cast(NormalizedCorporateAction, item)
        if action.kind == CorporateActionKind.SUBSCRIPTION:
            if quantity > 0:
                subscriptions.append(action.source_event_id)
            continue
        if quantity <= 0:
            continue

        projected_quantity = quantity * action.quantity_factor
        resolution = action.fractional_resolution

        if resolution is not None:
            if resolution.policy == FractionalResolutionPolicy.PENDING_SETTLEMENT:
                if (
                    resolution.settlement_price is not None
                    or str(resolution.cash_treatment or "").strip()
                ):
                    raise ValueError(
                        "PENDING_SETTLEMENT nao aceita valor ou tratamento de caixa"
                    )
                ledger_basis = str(resolution.ledger_basis or "").upper()
                if ledger_basis == "ADJUSTED_POST_EVENT":
                    # The ledger already reflects the issuer/exchange quantity
                    # adjustment. Preserve its tradable units and keep the
                    # unresolved residue as a separate pending item.
                    whole_quantity = quantity
                    projected_fraction = Decimal(0)
                    fractional_quantity = resolution.fractional_quantity
                    if fractional_quantity is None or fractional_quantity <= 0:
                        raise ValueError(
                            "ADJUSTED_POST_EVENT exige quantidade fracionaria evidenciada"
                        )
                    if fractional_quantity > quantity:
                        raise ValueError(
                            "ADJUSTED_POST_EVENT fractional_quantity invalida"
                        )
                    if fractional_quantity != fractional_quantity.to_integral_value():
                        raise ValueError(
                            "ADJUSTED_POST_EVENT fractional_quantity deve ser inteira"
                        )
                else:
                    whole_quantity = projected_quantity.to_integral_value(
                        rounding="ROUND_FLOOR"
                    )
                    projected_fraction = projected_quantity - whole_quantity
                    # Residue belongs to each portfolio ledger, not to the global
                    # event. Derive it here when reconciliation evidence only
                    # declares that settlement is pending.
                    fractional_quantity = (
                        resolution.fractional_quantity
                        if resolution.fractional_quantity is not None
                        else projected_fraction
                    )
                    if fractional_quantity < 0:
                        raise ValueError(
                            "PENDING_SETTLEMENT fractional_quantity nao pode ser negativa"
                        )
                    if fractional_quantity != projected_fraction:
                        raise ValueError(
                            "PENDING_SETTLEMENT fractional_quantity diverge da fracao projetada"
                        )
                if fractional_quantity > 0:
                    if resolution.fraction_is_post_event_quantity:
                        fractional_cost_brl = Decimal(0)
                        fractional_cost_original = Decimal(0)
                    else:
                        fractional_cost_ratio = (
                            fractional_quantity / projected_quantity
                        )
                        fractional_cost_brl = total_cost * fractional_cost_ratio
                        fractional_cost_original = (
                            total_cost_original_currency * fractional_cost_ratio
                        )
                    pending_corporate_action_fractions.append(
                        PendingCorporateActionFraction(
                            source_event_id=action.source_event_id,
                            event_date=action.event_date,
                            fractional_quantity=fractional_quantity,
                            cost_basis_brl=fractional_cost_brl,
                            cost_basis_original_currency=fractional_cost_original,
                        )
                    )
                    if not resolution.fraction_is_post_event_quantity:
                        total_cost -= fractional_cost_brl
                        total_cost_original_currency -= fractional_cost_original
                projected_quantity = whole_quantity
            elif resolution.policy == FractionalResolutionPolicy.CASH_SETTLEMENT:
                fractional_quantity = resolution.fractional_quantity
                settlement_price = resolution.settlement_price
                cash_treatment = str(resolution.cash_treatment or "").strip()

                if fractional_quantity is None or fractional_quantity <= 0:
                    raise ValueError(
                        "CASH_SETTLEMENT exige fractional_quantity positiva"
                    )

                if settlement_price is None or settlement_price < 0:
                    raise ValueError(
                        "CASH_SETTLEMENT exige settlement_price nao negativo"
                    )

                if not cash_treatment:
                    raise ValueError(
                        "CASH_SETTLEMENT exige cash_treatment"
                    )

                if fractional_quantity >= projected_quantity:
                    raise ValueError(
                        "CASH_SETTLEMENT possui fractional_quantity invalida"
                    )

                whole_quantity = projected_quantity.to_integral_value(
                    rounding="ROUND_FLOOR"
                )
                projected_fraction = projected_quantity - whole_quantity

                if fractional_quantity != projected_fraction:
                    raise ValueError(
                        "CASH_SETTLEMENT fractional_quantity diverge da fracao projetada"
                    )

                quantity_after_settlement = whole_quantity
                fractional_cost_ratio = (
                    fractional_quantity / projected_quantity
                )
                fractional_cost_basis = total_cost * fractional_cost_ratio
                fractional_cost_basis_original = (
                    total_cost_original_currency * fractional_cost_ratio
                )
                gross_amount = fractional_quantity * settlement_price
                fractional_realized_pnl = gross_amount - fractional_cost_basis

                total_cost -= fractional_cost_basis
                total_cost_original_currency -= fractional_cost_basis_original
                realized_pnl += fractional_realized_pnl

                corporate_action_cash_flows.append(
                    CanonicalCorporateActionCashFlow(
                        source_event_id=action.source_event_id,
                        event_date=action.event_date,
                        fractional_quantity=fractional_quantity,
                        unit_settlement_price_brl=settlement_price,
                        gross_amount_brl=gross_amount,
                        cash_treatment=cash_treatment,
                        cost_basis_brl=fractional_cost_basis,
                        realized_pnl_brl=fractional_realized_pnl,
                    )
                )

                projected_quantity = quantity_after_settlement

            if (
                resolution.policy
                == FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
                and projected_quantity != projected_quantity.to_integral_value()
            ):
                raise ValueError(
                    "NO_FRACTIONAL_RESIDUE incompativel com quantidade projetada"
                )

        quantity = projected_quantity
        applied.append(action.source_event_id)

    return PositionTimelineProjection(
        quantity=quantity,
        total_cost=total_cost,
        total_cost_original_currency=total_cost_original_currency,
        realized_pnl=realized_pnl,
        applied_event_ids=tuple(applied),
        subscription_event_ids=tuple(subscriptions),
        realized_disposals=tuple(disposals),
        corporate_action_cash_flows=tuple(corporate_action_cash_flows),
        pending_corporate_action_fractions=tuple(
            pending_corporate_action_fractions
        ),
    )
