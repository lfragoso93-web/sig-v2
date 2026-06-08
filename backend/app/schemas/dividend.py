from pydantic import BaseModel
from app.models.dividend import DividendType
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class DividendCreate(BaseModel):
    asset_id: int
    dividend_type: DividendType
    ex_date: date
    payment_date: Optional[date] = None
    value_per_unit: Decimal
    quantity_held: Decimal
    notes: Optional[str] = None


class DividendResponse(BaseModel):
    id: int
    portfolio_id: int
    asset_id: int
    dividend_type: DividendType
    ex_date: date
    payment_date: Optional[date] = None
    value_per_unit: Decimal
    quantity_held: Decimal
    total_value: Decimal
    is_automatic: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DividendSummaryResponse(BaseModel):
    by_type: dict[str, float]
    total: float
    year: Optional[int] = None
