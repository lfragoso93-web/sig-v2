"""Planos somente leitura para eventos de troca ou distribuição de ativos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from app.models.corporate_event import CorporateEvent, CorporateEventType


class CorporateExchangeProjectionError(ValueError):
    pass


@dataclass(frozen=True)
class CorporateExchangeProjectionPlan:
    event_id: int
    source_asset_id: int
    destination_asset_id: int
    source_quantity_before: Decimal
    source_quantity_after: Decimal
    destination_quantity_delta: Decimal
    destination_fractional_quantity: Decimal
    total_cost_before: Decimal
    allocated_source_cost: Decimal | None
    allocated_destination_cost: Decimal | None
    cash_component_total: Decimal
    cash_treatment: str | None
    executable: bool
    blocking_reasons: tuple[str, ...]


_SOURCE_TERMINATED_TYPES = {
    CorporateEventType.TICKER_CHANGE.value,
    CorporateEventType.CONVERSION.value,
    CorporateEventType.INCORPORATION.value,
    CorporateEventType.MERGER.value,
}


def build_corporate_exchange_projection_plan(
    event: CorporateEvent,
    *,
    source_quantity: Decimal,
    total_cost: Decimal,
    resolved_destination_asset_id: int | None = None,
) -> CorporateExchangeProjectionPlan:
    """Calcula quantidades, mas não executa nem inventa alocação de custo."""

    if source_quantity < 0 or total_cost < 0:
        raise CorporateExchangeProjectionError(
            "quantidade e custo devem ser não negativos"
        )
    destination_asset_id = event.destination_asset_id or resolved_destination_asset_id
    if destination_asset_id is None:
        raise CorporateExchangeProjectionError("ativo de destino não resolvido")

    event_type = str(getattr(event.event_type, "value", event.event_type)).upper()
    if event_type not in _SOURCE_TERMINATED_TYPES | {CorporateEventType.SPINOFF.value}:
        raise CorporateExchangeProjectionError("tipo não é troca ou cisão")

    factor = Decimal(str(event.quantity_factor))
    if not factor.is_finite() or factor <= 0:
        raise CorporateExchangeProjectionError("fator de quantidade inválido")

    destination_exact = source_quantity * factor
    quantity_step = Decimal(str(event.quantity_step)) if event.quantity_step else None
    destination_delta = destination_exact
    fractional_quantity = Decimal(0)
    if quantity_step is not None:
        if not quantity_step.is_finite() or quantity_step <= 0:
            raise CorporateExchangeProjectionError("passo de quantidade inválido")
        destination_delta = (destination_exact / quantity_step).to_integral_value(
            rounding=ROUND_FLOOR
        ) * quantity_step
        fractional_quantity = destination_exact - destination_delta
    source_after = (
        Decimal(0) if event_type in _SOURCE_TERMINATED_TYPES else source_quantity
    )
    cash_per_unit = Decimal(str(event.cash_component or 0))
    allocation = (
        Decimal(str(event.destination_cost_allocation))
        if event.destination_cost_allocation is not None
        else None
    )
    blocking: list[str] = []
    if event_type in _SOURCE_TERMINATED_TYPES:
        if allocation != 1:
            blocking.append("destination_cost_allocation_100_percent")
    elif allocation is None or not (0 < allocation < 1):
        blocking.append("destination_cost_allocation_between_0_and_1")

    fraction_cash = Decimal(0)
    if fractional_quantity:
        fraction_price = (
            Decimal(str(event.fractional_settlement_price))
            if event.fractional_settlement_price is not None
            else None
        )
        if (
            fraction_price is None
            or not fraction_price.is_finite()
            or fraction_price <= 0
        ):
            blocking.append("fractional_settlement_price")
        else:
            fraction_cash = fractional_quantity * fraction_price

    cash_total = source_quantity * cash_per_unit + fraction_cash
    cash_treatment = str(event.cash_treatment or "").upper() or None
    if cash_total and cash_treatment not in {
        "COST_REDUCTION",
        "TAXABLE_PROCEEDS",
        "NON_TAXABLE",
        "OTHER_REVIEWED",
    }:
        blocking.append("cash_treatment")

    destination_cost = total_cost * allocation if allocation is not None else None
    source_cost = (
        total_cost - destination_cost
        if destination_cost is not None
        and event_type == CorporateEventType.SPINOFF.value
        else Decimal(0)
        if destination_cost is not None
        else None
    )

    return CorporateExchangeProjectionPlan(
        event_id=int(event.id),
        source_asset_id=int(event.asset_id),
        destination_asset_id=int(destination_asset_id),
        source_quantity_before=source_quantity,
        source_quantity_after=source_after,
        destination_quantity_delta=destination_delta,
        destination_fractional_quantity=fractional_quantity,
        total_cost_before=total_cost,
        allocated_source_cost=source_cost,
        allocated_destination_cost=destination_cost,
        cash_component_total=cash_total,
        cash_treatment=cash_treatment,
        executable=not blocking,
        blocking_reasons=tuple(blocking),
    )
