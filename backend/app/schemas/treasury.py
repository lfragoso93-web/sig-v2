from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date
from decimal import Decimal

from app.models.treasury import TreasuryType


class TreasuryCreate(BaseModel):
    treasury_type: TreasuryType
    brapi_name: str                    # slug BRAPI ou nome exato
    date_purchase: date
    date_maturity: date
    quantity: Decimal
    purchase_price: Decimal
    invested_amount: Decimal
    rate_at_purchase: Decimal          # taxa contratada (ex: 10.5 = 10.5%)
    spread_rate: Optional[Decimal] = None
    is_active: bool = True

    @field_validator("quantity", "purchase_price", "invested_amount", "rate_at_purchase", mode="before")
    @classmethod
    def must_be_positive(cls, v):
        if v is not None and Decimal(str(v)) <= 0:
            raise ValueError("Deve ser maior que zero")
        return v


class TreasuryUpdate(BaseModel):
    treasury_type: Optional[TreasuryType] = None
    brapi_name: Optional[str] = None
    date_purchase: Optional[date] = None
    date_maturity: Optional[date] = None
    quantity: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None
    invested_amount: Optional[Decimal] = None
    rate_at_purchase: Optional[Decimal] = None
    spread_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None


class TreasuryResponse(BaseModel):
    id: int
    portfolio_id: int
    treasury_type: TreasuryType
    brapi_name: str
    date_purchase: date
    date_maturity: date
    quantity: float
    purchase_price: float
    invested_amount: float
    rate_at_purchase: float
    spread_rate: Optional[float] = None
    is_active: bool
    # Campos calculados (preenchidos pelo service ao buscar cotação)
    current_price: Optional[float] = None
    valor_atual: Optional[float] = None
    lucro_prejuizo: Optional[float] = None
    rentabilidade_pct: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
