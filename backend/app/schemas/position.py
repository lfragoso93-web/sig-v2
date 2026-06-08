from pydantic import BaseModel
from app.schemas.asset import AssetResponse
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PositionResponse(BaseModel):
    id: int
    portfolio_id: int
    asset_id: int
    asset: AssetResponse
    quantity: Decimal
    average_price: Decimal
    total_invested: Decimal
    realized_profit: Decimal
    # Campos calculados em tempo real (não persistidos)
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    unrealized_profit: Optional[Decimal] = None
    unrealized_profit_pct: Optional[Decimal] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    portfolio_id: int
    portfolio_name: str
    total_invested: Decimal
    current_value: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_return_pct: Optional[Decimal] = None
    realized_profit: Decimal
    positions_count: int
    positions: list[PositionResponse]
