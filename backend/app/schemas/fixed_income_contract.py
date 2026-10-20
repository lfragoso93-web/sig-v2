from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProductType = Literal[
    "CDB",
    "RDB",
    "LCI",
    "LCA",
    "LC",
    "LIG",
    "CRI",
    "CRA",
    "DEBENTURE",
    "DEBENTURE_INCENTIVADA",
    "LETRA_FINANCEIRA",
    "OUTRO",
]
Indexer = Literal["CDI", "SELIC", "IPCA_PLUS", "PREFIXADO", "IGPM_PLUS"]
RateUnit = Literal[
    "PERCENT_OF_INDEXER",
    "ANNUAL_PERCENT",
    "ANNUAL_SPREAD_PERCENT",
]
LiquidityType = Literal["DAILY", "AT_MATURITY", "CONTRACTUAL", "UNKNOWN"]


class FixedIncomeContractCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    product_type: ProductType
    issuer: str | None = Field(default=None, max_length=150)
    indexer: Indexer | None = None
    rate_value: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=8
    )
    rate_unit: RateUnit | None = None
    maturity_date: date | None = None
    liquidity_type: LiquidityType | None = None
    grace_period_end: date | None = None
    tax_exempt: bool | None = None
    currency: str = Field(default="BRL", min_length=1, max_length=10)

    @field_validator("display_name", "issuer")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("display_name")
    @classmethod
    def require_display_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("display_name is required")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_rate_contract(self) -> "FixedIncomeContractCreate":
        # IR treatment is a product rule, not user-entered contract metadata.
        self.tax_exempt = self.product_type in {
            "LCI", "LCA", "LIG", "CRI", "CRA", "DEBENTURE_INCENTIVADA"
        }
        if (self.rate_value is None) != (self.rate_unit is None):
            raise ValueError("rate_value and rate_unit must be provided together")

        expected_unit = None
        if self.indexer is not None:
            expected_unit = {
                "CDI": "PERCENT_OF_INDEXER",
                "SELIC": "PERCENT_OF_INDEXER",
                "PREFIXADO": "ANNUAL_PERCENT",
                "IPCA_PLUS": "ANNUAL_SPREAD_PERCENT",
                "IGPM_PLUS": "ANNUAL_SPREAD_PERCENT",
            }.get(self.indexer)
        if expected_unit and self.rate_unit and self.rate_unit != expected_unit:
            raise ValueError("rate_unit does not match the selected indexer")
        return self


class FixedIncomeContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    display_name: str
    product_type: ProductType
    issuer: str | None
    indexer: Indexer | None
    rate_value: Decimal | None
    rate_unit: RateUnit | None
    maturity_date: date | None
    liquidity_type: LiquidityType | None
    grace_period_end: date | None
    tax_exempt: bool | None
    currency: str
