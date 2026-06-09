from pydantic import BaseModel
from typing import Optional


class PositionOut(BaseModel):
    id:            int
    portfolio_id:  int
    ticker:        str
    asset_type:    str
    quantity:      float
    avg_price:     float
    current_price: Optional[float]
    current_value: Optional[float]

    # Campos calculados
    @property
    def invested(self) -> float:
        return self.avg_price * self.quantity

    @property
    def result_abs(self) -> float:
        cv = self.current_value if self.current_value is not None else self.invested
        return cv - self.invested

    @property
    def result_pct(self) -> float:
        inv = self.invested
        if inv == 0:
            return 0.0
        return self.result_abs / inv * 100

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_invested:   float
    total_current:    float
    result_abs:       float
    result_pct:       float
    positions_count:  int
