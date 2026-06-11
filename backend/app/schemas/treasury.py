from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date
from decimal import Decimal


class TreasuryCreate(BaseModel):
    brapi_name: str
    invested_value: Decimal
    purchase_date: date
    maturity_date: Optional[date] = None
    is_active: bool = True

    @field_validator("invested_value", mode="before")
    @classmethod
    def must_be_positive(cls, v):
        if v is not None and Decimal(str(v)) <= 0:
            raise ValueError("Valor investido deve ser maior que zero")
        return v


class TreasuryUpdate(BaseModel):
    brapi_name: Optional[str] = None
    invested_value: Optional[Decimal] = None
    purchase_date: Optional[date] = None
    maturity_date: Optional[date] = None
    is_active: Optional[bool] = None


class TreasuryResponse(BaseModel):
    id: int
    portfolio_id: int
    brapi_name: str
    invested_value: float
    purchase_date: date
    maturity_date: Optional[date] = None
    is_active: bool
    # Campos calculados on-the-fly
    current_price: Optional[float] = None
    valor_atual: Optional[float] = None
    lucro_prejuizo: Optional[float] = None
    rentabilidade_pct: Optional[float] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
