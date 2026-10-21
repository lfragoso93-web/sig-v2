"""Pure calculations for fractional rights from component-based bonuses."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Any


@dataclass(frozen=True)
class ComponentFractionalCashEntitlement:
    component: str
    bonus_quantity: Decimal
    whole_quantity: Decimal
    fractional_quantity: Decimal
    whole_units_formed: Decimal
    component_shares_in_units: Decimal
    residual_whole_quantity: Decimal
    settlement_price_brl: Decimal
    gross_amount_brl: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "bonus_quantity": self.bonus_quantity,
            "whole_quantity": self.whole_quantity,
            "fractional_quantity": self.fractional_quantity,
            "whole_units_formed": self.whole_units_formed,
            "component_shares_in_units": self.component_shares_in_units,
            "residual_whole_quantity": self.residual_whole_quantity,
            "settlement_price_brl": self.settlement_price_brl,
            "gross_amount_brl": self.gross_amount_brl,
        }


def derive_component_fractional_cash_entitlement(
    *,
    base_position: Decimal,
    bonus_factor: Decimal,
    components: list[dict[str, Any]],
    unit_composition: dict[str, Any] | None = None,
) -> tuple[ComponentFractionalCashEntitlement, ...]:
    """Derive cash rights by component, preserving each published price precision.

    ``units_per_position`` is the number of component shares represented by one
    held instrument. Only each component's fractional share quantity is valued;
    whole component shares remain outside this cash-right calculation.
    """

    if not base_position.is_finite() or base_position < 0:
        raise ValueError("base_position deve ser finita e nao negativa")
    if not bonus_factor.is_finite() or bonus_factor <= 0:
        raise ValueError("bonus_factor deve ser finito e positivo")
    if not components:
        raise ValueError("components deve conter ao menos um componente")

    output: list[ComponentFractionalCashEntitlement] = []
    quantities: dict[str, tuple[Decimal, Decimal, Decimal]] = {}
    seen: set[str] = set()
    for item in components:
        if not isinstance(item, dict):
            raise ValueError("cada component deve ser um objeto")
        component = str(item.get("component", "")).strip().upper()
        if not component or component in seen:
            raise ValueError("component deve ser unico e nao vazio")
        seen.add(component)
        units_per_position = Decimal(str(item["units_per_position"]))
        settlement_price = Decimal(str(item["settlement_price_brl"]))
        if not units_per_position.is_finite() or units_per_position <= 0:
            raise ValueError("units_per_position deve ser finito e positivo")
        if not settlement_price.is_finite() or settlement_price < 0:
            raise ValueError("settlement_price_brl deve ser finito e nao negativo")

        bonus_quantity = base_position * bonus_factor * units_per_position
        whole_quantity = bonus_quantity.to_integral_value(rounding=ROUND_FLOOR)
        fractional_quantity = bonus_quantity - whole_quantity
        quantities[component] = (
            bonus_quantity,
            whole_quantity,
            fractional_quantity,
        )
        output.append(
            ComponentFractionalCashEntitlement(
                component=component,
                bonus_quantity=bonus_quantity,
                whole_quantity=whole_quantity,
                fractional_quantity=fractional_quantity,
                whole_units_formed=Decimal(0),
                component_shares_in_units=Decimal(0),
                residual_whole_quantity=whole_quantity,
                settlement_price_brl=settlement_price,
                gross_amount_brl=fractional_quantity * settlement_price,
            )
        )

    if unit_composition is not None:
        if not isinstance(unit_composition, dict) or not unit_composition:
            raise ValueError("unit_composition deve mapear componentes para quantidades")
        normalized: dict[str, Decimal] = {}
        for raw_component, raw_quantity in unit_composition.items():
            component = str(raw_component).strip().upper()
            quantity = Decimal(str(raw_quantity))
            if (
                not component
                or component not in quantities
                or component in normalized
                or not quantity.is_finite()
                or quantity <= 0
            ):
                raise ValueError("composicao de Unit invalida")
            normalized[component] = quantity
        if set(normalized) != set(quantities):
            raise ValueError("composicao de Unit deve cobrir todos os componentes")
        units_formed = min(
            quantities[component][1] / required
            for component, required in normalized.items()
        ).to_integral_value(rounding=ROUND_FLOOR)
        replaced: list[ComponentFractionalCashEntitlement] = []
        for item in output:
            required = normalized[item.component]
            whole_units = units_formed
            residual_whole = item.whole_quantity - units_formed * required
            replaced.append(
                ComponentFractionalCashEntitlement(
                    component=item.component,
                    bonus_quantity=item.bonus_quantity,
                    whole_quantity=item.whole_quantity,
                    fractional_quantity=item.fractional_quantity,
                    whole_units_formed=whole_units,
                    component_shares_in_units=whole_units * required,
                    residual_whole_quantity=residual_whole,
                    settlement_price_brl=item.settlement_price_brl,
                    gross_amount_brl=item.gross_amount_brl,
                )
            )
        output = replaced
    return tuple(output)
