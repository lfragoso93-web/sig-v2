from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    BONIFICACAO = "BONIFICACAO"
    DESDOBRAMENTO = "DESDOBRAMENTO"
    GRUPAMENTO = "GRUPAMENTO"


class TransactionCreate(BaseModel):
    portfolio_id: int
    ticker: str
    asset_type: str
    transaction_type: TransactionType
    quantity: float
    price: float
    transaction_date: date
    broker: Optional[str] = None
    fees: Optional[float] = 0.0
    notes: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity", "price")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Deve ser maior que zero")
        return v


class TransactionOut(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    asset_type: str
    transaction_type: str
    quantity: float
    price: float
    total_value: float
    fees: float
    transaction_date: date
    broker: Optional[str]
    notes: Optional[str]
    average_price_after: Optional[float]

    class Config:
        from_attributes = True
