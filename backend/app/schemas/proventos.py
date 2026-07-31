"""Contratos públicos da API de Proventos."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.dividend_enums import DividendStatus, DividendType


class ProventosSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_recebido: float
    total_liquido_recebido: float
    total_bruto_recebido: float
    total_a_receber: float
    total_liquido_a_receber: float
    total_bruto_a_receber: float
    total_12m: float
    media_mensal_12m: float
    eventos_nao_cash: int = Field(ge=0)


class ProventoItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    ticker: str
    asset_type: str
    dividend_type: DividendType
    is_cash: bool
    status: DividendStatus

    record_date: date | None
    ex_date: date
    payment_date: date | None
    approved_on: date | None

    quantity: float
    value_per_unit: float
    gross_value_per_unit: float | None
    factor: float | None
    complete_factor: float | None
    total_value: float
    net_value: float

    isin_code: str | None
    asset_issued: str | None
    related_to: str | None
    remarks: str | None


class ProventosListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    items: list[ProventoItemResponse]


class ProventosAssetClassAmountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: str
    label: str
    value: float = Field(gt=0)


class ProventosMonthDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=1, le=12)
    total: float = Field(gt=0)
    by_asset_class: list[ProventosAssetClassAmountResponse]


class ProventosMonthlyHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int
    months: list[float | None] = Field(min_length=12, max_length=12)
    total: float
    media: float
    month_details: list[ProventosMonthDetailResponse]


class ProventosDistributionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    asset_type: str
    total: float
    percentage: float = Field(ge=0, le=100)
