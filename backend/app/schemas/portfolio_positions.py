from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PositionItemResponse(BaseModel):
    """Posição aberta materializada pelo valuation intradiário."""

    model_config = ConfigDict(extra="forbid")

    id: int
    ticker: str
    asset_type: str
    asset_label: str

    quantity: float
    average_price: float
    average_price_brl: float
    average_price_usd: float | None
    current_price: float | None
    current_price_brl: float | None
    current_price_usd: float | None

    current_value: float | None
    invested_value: float
    variation_value: float | None
    variation_percent: float | None
    allocation_pct: float

    logo_url: str | None
    is_usd: bool
    currency: Literal["BRL", "USD"]

    quote_updated_at: str | None = None
    applications_count: int | None = None
    maturity_date: str | None = None
    indexer: str | None = None
    rate_pct: float | None = None


class PositionGroupResponse(BaseModel):
    """Totais canônicos de uma classe e suas posições abertas."""

    model_config = ConfigDict(extra="forbid")

    label: str
    count: int = Field(ge=0)
    total_value: float
    total_invested: float
    positions: list[PositionItemResponse]

    daily_variation_value: float | None
    daily_variation_pct: float | None
    variation_pct: float | None
    variation_reference_date: str | None

    capital_result_value: float
    capital_result_pct: float | None
    received_dividends: float
    proventos_grupo: float
    total_result_value: float
    total_result_pct: float | None

    performance_source: Literal["intraday_valuation_and_received_dividends"]
    proventos_as_of: str
    target_pct: float | None
