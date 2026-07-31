from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CorporateEventReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class CorporateEventReviewRequest(BaseModel):
    decision: CorporateEventReviewDecision
    note: str = Field(min_length=10, max_length=2000)


class CorporateExchangeProjectionRequest(BaseModel):
    source_quantity: Decimal = Field(ge=0)
    total_cost: Decimal = Field(ge=0)


class CorporateExchangeProjectionResponse(BaseModel):
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
    blocking_reasons: list[str]


class CorporateEventReviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    ticker: str
    event_type: str
    effective_date: date
    quantity_factor: Decimal
    source_provider: str
    source_event_id: str | None
    reconciliation_status: str
    status: str
    is_canonical: bool
    requires_review: bool
    review_reason: str | None
    reviewed_at: datetime | None
    reviewed_by_user_id: int | None
    review_note: str | None


class CorporateEventReviewPage(BaseModel):
    items: list[CorporateEventReviewItem]
    total: int
    page: int
    page_size: int


class CorporateEventEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_provider: str
    source_event_id: str | None
    event_type: str
    effective_date: date
    record_date: date | None
    ex_date: date | None
    payment_date: date | None
    quantity_factor: Decimal
    cash_component: Decimal | None
    subscription_price: Decimal | None
    destination_cost_allocation: Decimal | None
    quantity_step: Decimal | None
    fractional_settlement_price: Decimal | None
    cash_treatment: str | None
    currency: str
    isin_code: str | None
    destination_isin_code: str | None
    reconciliation_status: str
    status: str
    is_canonical: bool
    raw_metadata: dict[str, object] | None


class CorporateEventEvidenceComparison(BaseModel):
    field: str
    values: dict[str, str | None]
    divergent: bool


class CorporateEventEvidenceGroup(BaseModel):
    selected_event_id: int
    reconciliation_group_hash: str | None
    evidences: list[CorporateEventEvidence]
    comparisons: list[CorporateEventEvidenceComparison]
    economic_effect: str
    terms_complete: bool
    automatic_application_supported: bool
    missing_terms: list[str]
    destination_resolution_status: str | None
    destination_asset_id: int | None
    destination_ticker: str | None
    destination_candidate_ids: list[int]
