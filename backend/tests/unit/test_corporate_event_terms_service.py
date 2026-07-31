from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.services.corporate_event_terms_service import (
    CorporateEventEconomicEffect,
    assess_corporate_event_terms,
)


def _event(event_type: str, **terms):
    defaults = {
        "event_type": event_type,
        "quantity_factor": Decimal(1),
        "subscription_price": None,
        "cash_component": None,
        "destination_asset_id": None,
        "destination_ticker": None,
        "destination_isin_code": None,
        "destination_cost_allocation": None,
        "quantity_step": None,
        "fractional_settlement_price": None,
        "cash_treatment": None,
    }
    return SimpleNamespace(**(defaults | terms))


@pytest.mark.parametrize(
    "event_type", ["CONVERSION", "INCORPORATION", "MERGER", "SPINOFF", "TICKER_CHANGE"]
)
def test_destination_events_require_destination_and_factor(event_type: str) -> None:
    incomplete = assess_corporate_event_terms(_event(event_type))
    complete = assess_corporate_event_terms(
        _event(
            event_type,
            destination_ticker="NEW3",
            quantity_factor=Decimal("0.5"),
            destination_cost_allocation=(
                Decimal("0.25") if event_type == "SPINOFF" else Decimal(1)
            ),
        )
    )

    assert incomplete.complete is False
    assert "destination_asset" in incomplete.missing_terms
    assert any(
        "destination_cost_allocation" in item for item in incomplete.missing_terms
    )
    assert complete.complete is True
    assert complete.automatic_application_supported is False
    assert (
        complete.economic_effect
        == CorporateEventEconomicEffect.DESTINATION_ASSET_EXCHANGE
    )


def test_subscription_requires_price_and_never_auto_applies() -> None:
    incomplete = assess_corporate_event_terms(_event("SUBSCRICAO"))
    complete = assess_corporate_event_terms(
        _event("SUBSCRICAO", subscription_price=Decimal("9.50"))
    )

    assert incomplete.missing_terms == ("subscription_price",)
    assert complete.complete is True
    assert complete.automatic_application_supported is False


def test_amortization_requires_positive_cash_component() -> None:
    assessment = assess_corporate_event_terms(
        _event(
            "AMORTIZATION",
            cash_component=Decimal("1.25"),
            cash_treatment="COST_REDUCTION",
        )
    )

    assert assessment.complete is True
    assert assessment.economic_effect == CorporateEventEconomicEffect.CASH
    assert assessment.automatic_application_supported is False


def test_delisting_requires_cash_or_destination_exchange() -> None:
    blocked = assess_corporate_event_terms(_event("DELISTING"))
    cash = assess_corporate_event_terms(
        _event(
            "DELISTING",
            cash_component=Decimal(12),
            cash_treatment="TAXABLE_PROCEEDS",
        )
    )

    assert blocked.complete is False
    assert blocked.missing_terms == ("cash_component_or_destination_exchange",)
    assert cash.complete is True


def test_simple_quantity_event_remains_automatically_supported() -> None:
    assessment = assess_corporate_event_terms(
        _event("BONIFICACAO", quantity_factor=Decimal("1.1"))
    )

    assert assessment.complete is True
    assert assessment.automatic_application_supported is True


def test_exchange_with_fraction_step_requires_settlement_price() -> None:
    assessment = assess_corporate_event_terms(
        _event(
            "MERGER",
            destination_ticker="NEW3",
            destination_cost_allocation=Decimal(1),
            quantity_step=Decimal(1),
        )
    )

    assert assessment.complete is False
    assert "fractional_settlement_price" in assessment.missing_terms


def test_exchange_cash_requires_explicit_treatment() -> None:
    assessment = assess_corporate_event_terms(
        _event(
            "MERGER",
            destination_ticker="NEW3",
            destination_cost_allocation=Decimal(1),
            cash_component=Decimal("1.5"),
        )
    )

    assert assessment.complete is False
    assert "cash_treatment" in assessment.missing_terms
