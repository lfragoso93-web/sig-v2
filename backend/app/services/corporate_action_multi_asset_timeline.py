"""Timeline expansion for issuer-evidenced component share bonuses.

The output consists of derived movements in memory. It never creates ledger
transactions. Fractional cash rights remain informational until a cash fact is
confirmed by the canonical event evidence.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Sequence

from app.services.corporate_action_engine import NormalizedCorporateAction
from app.services.corporate_action_fractional_entitlement import (
    derive_component_fractional_cash_entitlement,
)
from app.services.corporate_action_multi_asset_projection import (
    project_component_bonus_allocations,
)
from app.services.position_timeline_projection import (
    PositionMovement,
    PositionMovementKind,
    project_position_timeline,
)


@dataclass(frozen=True)
class ComponentBonusCashRight:
    source_event_id: str
    source_ticker: str
    component: str
    record_date: date
    settlement_date: date
    quantity: Decimal
    unit_price_brl: Decimal
    gross_amount_brl: Decimal
    attributed_cost_brl: Decimal
    status: str = "CALCULATED_NOT_CONFIRMED"


def _decimal(value: Any, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} invalido") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} deve ser finito")
    return parsed


def _project_one_component_bonus(
    *,
    action: NormalizedCorporateAction,
    spec: Mapping[str, Any],
    base_position: Decimal,
) -> tuple[tuple[tuple[str, str, Decimal, Decimal], ...], tuple[ComponentBonusCashRight, ...]]:
    source_event_id = action.source_event_id
    record_date = date.fromisoformat(str(spec["record_date"]))
    date.fromisoformat(str(spec["credit_date"]))
    settlement_date = date.fromisoformat(str(spec["settlement_date"]))
    bonus_factor = _decimal(spec["bonus_factor"], field="bonus_factor")
    bonus_cost_per_share = _decimal(
        spec["bonus_cost_per_share_brl"], field="bonus_cost_per_share_brl"
    )
    components = spec["components"]
    unit_composition = {
        str(key).strip().upper(): _decimal(value, field="unit_composition")
        for key, value in spec["unit_composition"].items()
    }
    if bonus_factor <= 0 or bonus_cost_per_share < 0:
        raise ValueError("fator e custo atribuido devem ser validos")
    if not isinstance(components, list) or not components:
        raise ValueError("components deve ser uma lista nao vazia")

    terms: dict[str, dict[str, Any]] = {}
    component_identities: dict[str, str] = {}
    for item in components:
        if not isinstance(item, dict):
            raise ValueError("cada componente deve ser objeto")
        name = str(item["component"]).strip().upper()
        if not name or name in terms:
            raise ValueError("componente duplicado ou vazio")
        terms[name] = item
        component_identities[name] = str(item["isin_code"])

    entitlements = derive_component_fractional_cash_entitlement(
        base_position=base_position,
        bonus_factor=bonus_factor,
        components=[
            {
                "component": name,
                "units_per_position": item["units_per_position"],
                "settlement_price_brl": item["settlement_price_brl"],
            }
            for name, item in terms.items()
        ],
        unit_composition=unit_composition,
    )
    total_bonus_shares = sum(
        (item.bonus_quantity for item in entitlements), Decimal(0)
    )
    bonus_cost_basis = total_bonus_shares * bonus_cost_per_share
    allocations: dict[str, Decimal] = {}
    if total_bonus_shares <= 0:
        raise ValueError("bonificacao sem quantidade positiva")
    if any(item.whole_units_formed > 0 for item in entitlements):
        shares_per_unit = sum(unit_composition.values(), Decimal(0))
        allocations["UNIT"] = (
            entitlements[0].whole_units_formed * shares_per_unit
            / total_bonus_shares
        )
    for item in entitlements:
        if item.residual_whole_quantity > 0:
            allocations[f"COMPONENT:{item.component}"] = (
                item.residual_whole_quantity / total_bonus_shares
            )
        if item.fractional_quantity > 0:
            allocations[f"CASH:{item.component}"] = (
                item.fractional_quantity / total_bonus_shares
            )
    if not allocations:
        raise ValueError("rateio de custo sem pernas")
    residual_key = sorted(allocations)[-1]
    allocations[residual_key] = Decimal(1) - sum(
        (value for key, value in allocations.items() if key != residual_key),
        Decimal(0),
    )

    projection = project_component_bonus_allocations(
        entitlements=entitlements,
        component_identities=component_identities,
        unit_identity=str(spec["unit_isin_code"]),
        unit_composition=unit_composition,
        bonus_cost_basis_brl=bonus_cost_basis,
        cost_allocations=allocations,
    )
    exact_cost_by_asset_kind: dict[str, Decimal] = {}
    for leg in projection.asset_legs:
        if leg.asset_kind == "UNIT":
            shares_per_unit = sum(unit_composition.values(), Decimal(0))
            attributed_shares = leg.quantity * shares_per_unit
        else:
            attributed_shares = leg.quantity
        exact_cost_by_asset_kind[leg.asset_kind] = (
            attributed_shares * bonus_cost_per_share
        )
    exact_asset_legs = tuple(
        replace(
            leg,
            cost_basis_brl=exact_cost_by_asset_kind[leg.asset_kind],
            cost_allocation=(
                exact_cost_by_asset_kind[leg.asset_kind] / bonus_cost_basis
                if bonus_cost_basis
                else leg.cost_allocation
            ),
        )
        for leg in projection.asset_legs
    )
    exact_cash_legs = tuple(
        replace(
            leg,
            cost_basis_brl=leg.quantity * bonus_cost_per_share,
            cost_allocation=(
                (leg.quantity * bonus_cost_per_share) / bonus_cost_basis
                if bonus_cost_basis
                else leg.cost_allocation
            ),
            realized_pnl_brl=(
                leg.gross_amount_brl - leg.quantity * bonus_cost_per_share
            ),
        )
        for leg in projection.fractional_cash_legs
    )
    unit_ticker = str(spec["unit_ticker"]).strip().upper()
    unit_asset_type = str(spec["unit_asset_type"]).strip().upper()
    movements: list[tuple[str, str, Decimal, Decimal]] = []
    for leg in exact_asset_legs:
        if leg.asset_kind == "UNIT":
            ticker, asset_type = unit_ticker, unit_asset_type
        else:
            component = leg.asset_kind.removeprefix("COMPONENT:")
            ticker = str(terms[component]["ticker"]).strip().upper()
            asset_type = str(terms[component]["asset_type"]).strip().upper()
        if not ticker or not asset_type or leg.quantity <= 0:
            raise ValueError("perna de ativo nao resolvida")
        movements.append((ticker, asset_type, leg.quantity, leg.cost_basis_brl))

    rights = tuple(
        ComponentBonusCashRight(
            source_event_id=source_event_id,
            source_ticker=action.ticker,
            component=leg.component,
            record_date=record_date,
            settlement_date=settlement_date,
            quantity=leg.quantity,
            unit_price_brl=leg.settlement_price_brl,
            gross_amount_brl=leg.gross_amount_brl,
            attributed_cost_brl=leg.cost_basis_brl,
        )
        for leg in exact_cash_legs
    )
    return tuple(movements), rights


def expand_component_bonus_movements(
    *,
    movements_by_ticker: dict[str, list[PositionMovement]],
    metadata_by_ticker: dict[str, tuple[str, bool]],
    actions_by_ticker: Mapping[str, Sequence[NormalizedCorporateAction]],
    target_date: date,
) -> dict[str, tuple[ComponentBonusCashRight, ...]]:
    """Add issuer-evidenced bonus legs to in-memory timelines through a date."""

    bonus_actions = sorted(
        (
            action
            for actions in actions_by_ticker.values()
            for action in actions
            if action.component_bonus is not None
            and action.event_date <= target_date
        ),
        key=lambda action: (action.event_date, action.source_event_id),
    )
    rights_by_ticker: dict[str, list[ComponentBonusCashRight]] = defaultdict(list)
    for action in bonus_actions:
        spec = action.component_bonus
        assert spec is not None
        source_ticker = action.ticker.strip().upper()
        if source_ticker not in movements_by_ticker:
            continue
        record_date = date.fromisoformat(str(spec["record_date"]))
        eligible_actions = tuple(
            prior
            for prior in actions_by_ticker.get(source_ticker, ())
            if prior.component_bonus is None
        )
        base = project_position_timeline(
            movements=tuple(movements_by_ticker[source_ticker]),
            actions=eligible_actions,
            through_date=record_date,
        )
        if base.quantity <= 0:
            continue
        asset_movements, rights = _project_one_component_bonus(
            action=action,
            spec=spec,
            base_position=base.quantity,
        )
        credit_date = date.fromisoformat(str(spec["credit_date"]))
        for ticker, asset_type, quantity, cost_basis in asset_movements:
            movements_by_ticker.setdefault(ticker, []).append(
                PositionMovement(
                    movement_date=credit_date,
                    # The issuer's credit date controls when new asset legs
                    # become transferable positions; the record date controls
                    # portfolio entitlement.
                    kind=PositionMovementKind.BUY,
                    quantity=quantity,
                    unit_price=cost_basis / quantity,
                    transaction_id=f"corporate-action:{action.source_event_id}",
                    ticker=ticker,
                    asset_type=asset_type,
                    corporate_action_event_id=action.source_event_id,
                )
            )
            metadata_by_ticker.setdefault(ticker, (asset_type, False))
        rights_by_ticker[source_ticker].extend(rights)
    return {ticker: tuple(items) for ticker, items in rights_by_ticker.items()}
