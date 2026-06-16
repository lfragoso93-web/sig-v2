from pydantic import BaseModel
from typing import Optional
from datetime import date


class DividendCreate(BaseModel):
    ticker: str
    ex_date: date
    payment_date: Optional[date] = None
    value_per_unit: float
    dividend_type: Optional[str] = None


class DividendRead(DividendCreate):
    id: int
    total_received: Optional[float] = None
    portfolio_id: Optional[int] = None

    class Config:
        from_attributes = True


# Alias de compatibilidade usado pelos routers
DividendResponse = DividendRead
