from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.services.corporate_exchange_projection_service import (
    CorporateExchangeProjectionError,
    build_corporate_exchange_projection_plan,
)


def _event(event_type: str, **values):
    defaults = {
        "id": 91,
        "asset_id": 7,
        "destination_asset_id": 8,
        "event_type": event_type,
        "quantity_factor": Decimal("0.5"),
        "cash_component": None,
        "destination_cost_allocation": Decimal(1),
        "quantity_step": None,
        "fractional_settlement_price": None,
        "cash_treatment": None,
    }
    return SimpleNamespace(**(defaults | values))


def test_merger_plan_terminates_source_and_calculates_destination_quantity() -> None:
    plan = build_corporate_exchange_projection_plan(
        _event("MERGER"),
        source_quantity=Decimal(100),
        total_cost=Decimal(2500),
    )

    assert plan.source_quantity_after == 0
    assert plan.destination_quantity_delta == Decimal(50)
    assert plan.allocated_destination_cost == Decimal(2500)
    assert plan.allocated_source_cost == 0
    assert plan.executable is True
    assert plan.blocking_reasons == ()


def test_spinoff_keeps_source_and_requires_cost_allocation() -> None:
    plan = build_corporate_exchange_projection_plan(
        _event(
            "SPINOFF",
            quantity_factor=Decimal("0.2"),
            destination_cost_allocation=Decimal("0.3"),
        ),
        source_quantity=Decimal(100),
        total_cost=Decimal(2500),
    )

    assert plan.source_quantity_after == Decimal(100)
    assert plan.destination_quantity_delta == Decimal(20)
    assert plan.allocated_source_cost == Decimal(1750)
    assert plan.allocated_destination_cost == Decimal(750)
    assert plan.executable is True


def test_cash_component_is_exposed_without_assuming_tax_treatment() -> None:
    plan = build_corporate_exchange_projection_plan(
        _event(
            "CONVERSION",
            cash_component=Decimal("1.25"),
            cash_treatment="TAXABLE_PROCEEDS",
        ),
        source_quantity=Decimal(80),
        total_cost=Decimal(1000),
    )

    assert plan.cash_component_total == Decimal(100)
    assert plan.cash_treatment == "TAXABLE_PROCEEDS"
    assert plan.executable is True


def test_fraction_is_settled_only_with_explicit_step_and_price() -> None:
    plan = build_corporate_exchange_projection_plan(
        _event(
            "MERGER",
            quantity_factor=Decimal("0.333"),
            quantity_step=Decimal(1),
            fractional_settlement_price=Decimal(12),
            cash_treatment="TAXABLE_PROCEEDS",
        ),
        source_quantity=Decimal(10),
        total_cost=Decimal(100),
    )

    assert plan.destination_quantity_delta == Decimal(3)
    assert plan.destination_fractional_quantity == Decimal("0.330")
    assert plan.cash_component_total == Decimal("3.960")
    assert plan.executable is True


def test_plan_requires_resolved_destination() -> None:
    with pytest.raises(CorporateExchangeProjectionError, match="não resolvido"):
        build_corporate_exchange_projection_plan(
            _event("MERGER", destination_asset_id=None),
            source_quantity=Decimal(100),
            total_cost=Decimal(1000),
        )
