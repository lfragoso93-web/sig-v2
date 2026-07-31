"""Validação dos termos econômicos necessários para eventos corporativos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.models.corporate_event import CorporateEvent, CorporateEventType


class CorporateEventEconomicEffect(StrEnum):
    SAME_ASSET_QUANTITY = "SAME_ASSET_QUANTITY"
    SUBSCRIPTION_RIGHT = "SUBSCRIPTION_RIGHT"
    DESTINATION_ASSET_EXCHANGE = "DESTINATION_ASSET_EXCHANGE"
    CASH = "CASH"
    TERMINATION = "TERMINATION"


@dataclass(frozen=True)
class CorporateEventTermsAssessment:
    event_type: str
    economic_effect: CorporateEventEconomicEffect
    complete: bool
    automatic_application_supported: bool
    missing_terms: tuple[str, ...]


_SAME_ASSET_QUANTITY_TYPES = {
    CorporateEventType.DESDOBRAMENTO.value,
    CorporateEventType.GRUPAMENTO.value,
    CorporateEventType.BONIFICACAO.value,
}
_DESTINATION_EXCHANGE_TYPES = {
    CorporateEventType.TICKER_CHANGE.value,
    CorporateEventType.CONVERSION.value,
    CorporateEventType.INCORPORATION.value,
    CorporateEventType.MERGER.value,
    CorporateEventType.SPINOFF.value,
}
_SOURCE_TERMINATED_TYPES = _DESTINATION_EXCHANGE_TYPES - {
    CorporateEventType.SPINOFF.value
}
_CASH_TREATMENTS = {
    "COST_REDUCTION",
    "TAXABLE_PROCEEDS",
    "NON_TAXABLE",
    "OTHER_REVIEWED",
}


def _positive(value: object) -> bool:
    if value is None:
        return False
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return parsed.is_finite() and parsed > 0


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _has_destination(event: CorporateEvent) -> bool:
    return bool(
        event.destination_asset_id
        or str(event.destination_ticker or "").strip()
        or str(event.destination_isin_code or "").strip()
    )


def assess_corporate_event_terms(
    event: CorporateEvent,
) -> CorporateEventTermsAssessment:
    """Classifica o efeito e informa os termos ausentes sem aplicar o evento."""

    event_type = str(getattr(event.event_type, "value", event.event_type)).upper()
    missing: list[str] = []

    if event_type in _SAME_ASSET_QUANTITY_TYPES:
        if not _positive(event.quantity_factor):
            missing.append("quantity_factor")
        return CorporateEventTermsAssessment(
            event_type=event_type,
            economic_effect=CorporateEventEconomicEffect.SAME_ASSET_QUANTITY,
            complete=not missing,
            automatic_application_supported=not missing,
            missing_terms=tuple(missing),
        )

    if event_type == CorporateEventType.SUBSCRICAO.value:
        if not _positive(event.subscription_price):
            missing.append("subscription_price")
        return CorporateEventTermsAssessment(
            event_type=event_type,
            economic_effect=CorporateEventEconomicEffect.SUBSCRIPTION_RIGHT,
            complete=not missing,
            automatic_application_supported=False,
            missing_terms=tuple(missing),
        )

    if event_type in _DESTINATION_EXCHANGE_TYPES:
        if not _has_destination(event):
            missing.append("destination_asset")
        if not _positive(event.quantity_factor):
            missing.append("quantity_factor")
        allocation = _decimal(event.destination_cost_allocation)
        if event_type in _SOURCE_TERMINATED_TYPES:
            if allocation != 1:
                missing.append("destination_cost_allocation_100_percent")
        elif allocation is None or not (0 < allocation < 1):
            missing.append("destination_cost_allocation_between_0_and_1")
        if event.quantity_step is not None:
            if not _positive(event.quantity_step):
                missing.append("positive_quantity_step")
            if not _positive(event.fractional_settlement_price):
                missing.append("fractional_settlement_price")
        if (
            _positive(event.cash_component)
            and str(event.cash_treatment or "").upper() not in _CASH_TREATMENTS
        ):
            missing.append("cash_treatment")
        return CorporateEventTermsAssessment(
            event_type=event_type,
            economic_effect=CorporateEventEconomicEffect.DESTINATION_ASSET_EXCHANGE,
            complete=not missing,
            automatic_application_supported=False,
            missing_terms=tuple(missing),
        )

    if event_type == CorporateEventType.AMORTIZATION.value:
        if not _positive(event.cash_component):
            missing.append("cash_component")
        if str(event.cash_treatment or "").upper() not in _CASH_TREATMENTS:
            missing.append("cash_treatment")
        return CorporateEventTermsAssessment(
            event_type=event_type,
            economic_effect=CorporateEventEconomicEffect.CASH,
            complete=not missing,
            automatic_application_supported=False,
            missing_terms=tuple(missing),
        )

    if event_type == CorporateEventType.DELISTING.value:
        has_cash = _positive(event.cash_component)
        has_exchange = _has_destination(event) and _positive(event.quantity_factor)
        if not has_cash and not has_exchange:
            missing.append("cash_component_or_destination_exchange")
        if has_cash and str(event.cash_treatment or "").upper() not in _CASH_TREATMENTS:
            missing.append("cash_treatment")
        return CorporateEventTermsAssessment(
            event_type=event_type,
            economic_effect=CorporateEventEconomicEffect.TERMINATION,
            complete=not missing,
            automatic_application_supported=False,
            missing_terms=tuple(missing),
        )

    return CorporateEventTermsAssessment(
        event_type=event_type,
        economic_effect=CorporateEventEconomicEffect.TERMINATION,
        complete=False,
        automatic_application_supported=False,
        missing_terms=("supported_event_type",),
    )
