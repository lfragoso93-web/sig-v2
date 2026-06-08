from pydantic import BaseModel, field_validator, model_validator
from app.models.transaction import TransactionType
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class TransactionCreate(BaseModel):
    asset_id: int
    transaction_type: TransactionType
    date: date
    quantity: Decimal
    unit_price: Decimal
    fees: Decimal = Decimal("0")
    broker: Optional[str] = None
    notes: Optional[str] = None
    is_day_trade: bool = False

    @field_validator("quantity", "unit_price")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Deve ser maior que zero")
        return v

    @field_validator("fees")
    @classmethod
    def fees_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Taxas não podem ser negativas")
        return v


class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    asset_id: int
    transaction_type: TransactionType
    date: date
    quantity: Decimal
    unit_price: Decimal
    total_cost: Decimal
    fees: Decimal
    broker: Optional[str] = None
    notes: Optional[str] = None
    is_day_trade: bool
    created_at: datetime

    model_config = {"from_attributes": True}
