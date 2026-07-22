from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class DividendCreate(BaseModel):
    ticker: str
    ex_date: date
    payment_date: Optional[date] = None
    value_per_unit: float
    dividend_type: Optional[str] = None


class DividendRead(DividendCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_received: Optional[float] = None
    portfolio_id: Optional[int] = None


# Alias de compatibilidade usado pelos routers
DividendResponse = DividendRead
