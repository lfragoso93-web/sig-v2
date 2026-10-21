"""Pure fail-closed allocation of component bonuses across portfolio assets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from typing import Mapping

from app.services.corporate_action_fractional_entitlement import (
    ComponentFractionalCashEntitlement,
)


def _normalize_isin(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().upper()
    if (
        len(normalized) != 12
        or not normalized.isalnum()
        or not normalized[:2].isalpha()
        or not normalized[-1].isdigit()
    ):
        raise ValueError(f"{field} deve ser um ISIN de 12 caracteres")
    expanded = "".join(
        str(ord(character) - ord("A") + 10)
        if character.isalpha()
        else character
        for character in normalized
    )
    checksum = 0
    for offset, character in enumerate(reversed(expanded)):
        digit = int(character)
        if offset % 2 == 1:
            digit *= 2
        checksum += digit // 10 + digit % 10
    if checksum % 10 != 0:
        raise ValueError(f"{field} possui digito de controle invalido")
    return normalized


@dataclass(frozen=True)
class BonusAssetLeg:
    """One resolved asset leg with quantity and allocated portfolio cost."""

    identity: str
    asset_kind: str
    quantity: Decimal
    cost_allocation: Decimal
    cost_basis_brl: Decimal


@dataclass(frozen=True)
class BonusFractionalCashLeg:
    """A fractional component sold for cash, separate from asset quantities."""

    component: str
    quantity: Decimal
    settlement_price_brl: Decimal
    gross_amount_brl: Decimal
    cost_allocation: Decimal
    cost_basis_brl: Decimal
    realized_pnl_brl: Decimal


@dataclass(frozen=True)
class MultiAssetBonusProjection:
    """Read-only event output; it does not mutate transactions or positions."""

    asset_legs: tuple[BonusAssetLeg, ...]
    fractional_cash_legs: tuple[BonusFractionalCashLeg, ...]
    bonus_cost_basis_brl: Decimal
    allocated_total_cost_brl: Decimal


def project_component_bonus_allocations(
    *,
    entitlements: tuple[ComponentFractionalCashEntitlement, ...],
    component_identities: Mapping[str, str],
    unit_identity: str | None,
    unit_composition: Mapping[str, Decimal] | None,
    bonus_cost_basis_brl: Decimal,
    cost_allocations: Mapping[str, Decimal],
) -> MultiAssetBonusProjection:
    """Allocate an already-derived bonus using explicit destination identities.

    Cost allocation keys are ``UNIT`` (when formed), ``COMPONENT:<name>`` for
    each residual whole-share leg, and ``CASH:<name>`` for each fractional leg.
    Every allocation is mandatory and the exact sum must be one. The function
    deliberately does not infer cost from quantities or market prices.
    """

    if not entitlements:
        raise ValueError("entitlements nao pode estar vazio")
    if not bonus_cost_basis_brl.is_finite() or bonus_cost_basis_brl < 0:
        raise ValueError("bonus_cost_basis_brl deve ser finito e nao negativo")

    by_component = {item.component.strip().upper(): item for item in entitlements}
    if len(by_component) != len(entitlements):
        raise ValueError("componentes duplicados")
    if any(not component for component in by_component):
        raise ValueError("componente vazio")
    for component, item in by_component.items():
        quantities = (
            item.bonus_quantity,
            item.whole_quantity,
            item.fractional_quantity,
            item.whole_units_formed,
            item.component_shares_in_units,
            item.residual_whole_quantity,
            item.settlement_price_brl,
            item.gross_amount_brl,
        )
        if any(not value.is_finite() for value in quantities):
            raise ValueError(f"quantidades e valores de {component} devem ser finitos")
        if any(value < 0 for value in quantities):
            raise ValueError(f"quantidades e valores de {component} nao podem ser negativos")
        if item.whole_quantity != item.whole_quantity.to_integral_value():
            raise ValueError(f"whole_quantity de {component} deve ser inteira")
        if item.whole_units_formed != item.whole_units_formed.to_integral_value():
            raise ValueError("whole_units_formed deve ser inteira")
        if item.fractional_quantity >= 1:
            raise ValueError(f"fractional_quantity de {component} deve ser menor que um")
        if item.bonus_quantity != item.whole_quantity + item.fractional_quantity:
            raise ValueError(f"quantidade total de {component} diverge de inteira e fracao")
        if (
            item.component_shares_in_units
            + item.residual_whole_quantity
            != item.whole_quantity
        ):
            raise ValueError(f"quantidade inteira de {component} nao foi alocada")
        if (
            item.component_shares_in_units
            != item.component_shares_in_units.to_integral_value()
        ):
            raise ValueError(f"acoes de {component} em Units devem ser inteiras")
        if item.gross_amount_brl != item.fractional_quantity * item.settlement_price_brl:
            raise ValueError(f"valor bruto de {component} diverge da fracao e preco")

    normalized_identities: dict[str, str] = {}
    for key, value in component_identities.items():
        component = str(key).strip().upper()
        if not component or component in normalized_identities:
            raise ValueError("identidades de componente duplicadas ou vazias")
        normalized_identities[component] = _normalize_isin(
            value, field=f"ISIN do componente {component}"
        )
    if set(normalized_identities) != set(by_component):
        raise ValueError("cada componente deve resolver para uma identidade de ativo")
    if len(set(normalized_identities.values())) != len(normalized_identities):
        raise ValueError("cada componente deve resolver para um ISIN distinto")

    has_unit_leg = any(item.whole_units_formed > 0 for item in entitlements)
    normalized_unit_identity = (
        _normalize_isin(unit_identity, field="ISIN da Unit")
        if unit_identity
        else ""
    )
    if has_unit_leg and not normalized_unit_identity:
        raise ValueError("Unit formada exige identidade de destino resolvida")
    if unit_composition is None and has_unit_leg:
        raise ValueError("Unit formada exige composicao evidenciada")

    normalized_composition: dict[str, Decimal] = {}
    for key, value in (unit_composition or {}).items():
        component = str(key).strip().upper()
        if not component or component in normalized_composition:
            raise ValueError("composicao de Unit contem componentes duplicados")
        normalized_composition[component] = Decimal(str(value))
    expected_components = set(by_component)
    if has_unit_leg and set(normalized_composition) != expected_components:
        raise ValueError("composicao deve cobrir os componentes da bonificacao")
    if any(not value.is_finite() or value <= 0 for value in normalized_composition.values()):
        raise ValueError("composicao deve conter quantidades positivas")
    if any(value != value.to_integral_value() for value in normalized_composition.values()):
        raise ValueError("composicao de Unit deve usar quantidades inteiras")
    if has_unit_leg:
        if normalized_unit_identity in normalized_identities.values():
            raise ValueError("ISIN da Unit deve diferir dos ISINs de componentes")
        unit_counts = {item.whole_units_formed for item in entitlements}
        if len(unit_counts) != 1:
            raise ValueError("quantidade de Units formadas diverge entre componentes")

    expected_keys: set[str] = set()
    if has_unit_leg:
        expected_keys.add("UNIT")
    for component, item in by_component.items():
        if item.residual_whole_quantity > 0:
            expected_keys.add(f"COMPONENT:{component}")
        if item.fractional_quantity > 0:
            expected_keys.add(f"CASH:{component}")

    allocations = {key.strip().upper(): Decimal(str(value)) for key, value in cost_allocations.items()}
    if set(allocations) != expected_keys:
        raise ValueError("rateio de custo deve cobrir exatamente cada perna de ativo e caixa")
    if any(not value.is_finite() or value < 0 or value > 1 for value in allocations.values()):
        raise ValueError("cada parcela de custo deve estar entre zero e um")
    if sum(allocations.values(), Decimal(0)) != Decimal(1):
        raise ValueError("rateio de custo deve somar exatamente um")

    asset_legs: list[BonusAssetLeg] = []
    cash_legs: list[BonusFractionalCashLeg] = []
    with localcontext() as context:
        context.prec = max(context.prec, 60)
        for component, item in sorted(by_component.items()):
            shares_in_units = item.component_shares_in_units
            if shares_in_units > 0:
                required = normalized_composition[component]
                if shares_in_units != item.whole_units_formed * required:
                    raise ValueError("quantidade alocada a Units diverge da composicao")
            if (
                shares_in_units + item.residual_whole_quantity
                + item.fractional_quantity != item.bonus_quantity
            ):
                raise ValueError("quantidade do componente nao foi conservada")

            if item.residual_whole_quantity > 0:
                key = f"COMPONENT:{component}"
                asset_legs.append(
                    BonusAssetLeg(
                        identity=normalized_identities[component],
                        asset_kind=f"COMPONENT:{component}",
                        quantity=item.residual_whole_quantity,
                        cost_allocation=allocations[key],
                        cost_basis_brl=bonus_cost_basis_brl * allocations[key],
                    )
                )
            if item.fractional_quantity > 0:
                key = f"CASH:{component}"
                gross = item.fractional_quantity * item.settlement_price_brl
                cost_basis = bonus_cost_basis_brl * allocations[key]
                cash_legs.append(
                    BonusFractionalCashLeg(
                        component=component,
                        quantity=item.fractional_quantity,
                        settlement_price_brl=item.settlement_price_brl,
                        gross_amount_brl=gross,
                        cost_allocation=allocations[key],
                        cost_basis_brl=cost_basis,
                        realized_pnl_brl=gross - cost_basis,
                    )
                )

        if has_unit_leg:
            unit_count = min(
                by_component[component].component_shares_in_units / required
                for component, required in normalized_composition.items()
            )
            asset_legs.append(
                BonusAssetLeg(
                    identity=normalized_unit_identity,
                    asset_kind="UNIT",
                    quantity=unit_count,
                    cost_allocation=allocations["UNIT"],
                    cost_basis_brl=bonus_cost_basis_brl * allocations["UNIT"],
                )
            )

        allocated_cost = sum(
            (leg.cost_basis_brl for leg in asset_legs), Decimal(0)
        ) + sum((leg.cost_basis_brl for leg in cash_legs), Decimal(0))
        residual_cost = bonus_cost_basis_brl - allocated_cost
        if residual_cost:
            if cash_legs:
                last = cash_legs[-1]
                adjusted_cost = last.cost_basis_brl + residual_cost
                cash_legs[-1] = replace(
                    last,
                    cost_allocation=(
                        adjusted_cost / bonus_cost_basis_brl
                        if bonus_cost_basis_brl
                        else last.cost_allocation
                    ),
                    cost_basis_brl=adjusted_cost,
                    realized_pnl_brl=last.gross_amount_brl - adjusted_cost,
                )
            elif asset_legs:
                last = asset_legs[-1]
                adjusted_cost = last.cost_basis_brl + residual_cost
                asset_legs[-1] = replace(
                    last,
                    cost_allocation=(
                        adjusted_cost / bonus_cost_basis_brl
                        if bonus_cost_basis_brl
                        else last.cost_allocation
                    ),
                    cost_basis_brl=adjusted_cost,
                )
            allocated_cost = sum(
                (leg.cost_basis_brl for leg in asset_legs), Decimal(0)
            ) + sum((leg.cost_basis_brl for leg in cash_legs), Decimal(0))
        if allocated_cost != bonus_cost_basis_brl:
            raise ValueError(
                "projecao nao preservou o custo-base da bonificacao: "
                f"allocated={allocated_cost} expected={bonus_cost_basis_brl}"
            )

    return MultiAssetBonusProjection(
        asset_legs=tuple(asset_legs),
        fractional_cash_legs=tuple(cash_legs),
        bonus_cost_basis_brl=bonus_cost_basis_brl,
        allocated_total_cost_brl=allocated_cost,
    )
