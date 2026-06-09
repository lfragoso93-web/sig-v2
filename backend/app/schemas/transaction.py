from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from enum import Enum


class OperationType(str, Enum):
    buy  = "buy"
    sell = "sell"


class TransactionCreate(BaseModel):
    ticker:     str
    asset_type: str
    operation:  OperationType
    quantity:   float = Field(gt=0)
    price:      float = Field(gt=0)
    fees:       float = Field(default=0.0, ge=0)
    date:       date
    notes:      Optional[str] = None


class TransactionOut(BaseModel):
    id:         int
    portfolio_id: int
    ticker:     str
    asset_type: str
    operation:  OperationType
    quantity:   float
    price:      float
    fees:       float
    date:       date
    notes:      Optional[str]

    class Config:
        from_attributes = True
