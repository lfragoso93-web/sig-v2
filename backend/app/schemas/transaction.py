from pydantic import BaseModel
from typing import Optional
from datetime import date


class TransactionCreate(BaseModel):
    ticker:     str
    asset_type: str
    operation:  str
    quantity:   float
    price:      float
    fees:       Optional[float] = 0.0
    date:       date
    currency:   Optional[str]  = "BRL"
    notes:      Optional[str]  = None


class TransactionUpdate(BaseModel):
    ticker:     Optional[str] = None
    asset_type: Optional[str] = None
    operation:  Optional[str] = None
    quantity:   Optional[float] = None
    price:      Optional[float] = None
    fees:       Optional[float] = None
    date:       Optional[date] = None
    currency:   Optional[str] = None
    notes:      Optional[str] = None


class TransactionOut(BaseModel):
    id:           int
    portfolio_id: int
    ticker:       str
    asset_type:   str
    operation:    str
    quantity:     float
    price:        float
    fees:         float
    date:         date
    currency:     str
    notes:        Optional[str]

    model_config = {"from_attributes": True}
