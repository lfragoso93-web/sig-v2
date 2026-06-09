from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
from datetime import datetime


class AssetMinimal(BaseModel):
    """Subconjunto de Asset embutido na resposta de posição."""
    id:           int
    ticker:       str
    name:         str
    asset_type:   str
    brapi_ticker: Optional[str] = None

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """Posição individual enriquecida com preço atual (quando disponível)."""
    id:                    int
    portfolio_id:          int
    asset_id:              int
    asset:                 AssetMinimal
    quantity:              Decimal
    average_price:         Decimal
    total_invested:        Decimal
    realized_profit:       Decimal
    current_price:         Optional[Decimal] = None
    current_value:         Optional[Decimal] = None
    unrealized_profit:     Optional[Decimal] = None
    unrealized_profit_pct: Optional[Decimal] = None
    updated_at:            Optional[datetime] = None

    class Config:
        from_attributes = True


# Alias mantido para retrocompatibilidade interna
PositionOut = PositionResponse


class PortfolioSummary(BaseModel):
    """Resumo completo da carteira retornado pelo endpoint /summary."""
    portfolio_id:       int
    portfolio_name:     str
    total_invested:     Decimal
    current_value:      Optional[Decimal] = None
    total_return:       Optional[Decimal] = None
    total_return_pct:   Optional[Decimal] = None
    realized_profit:    Decimal
    positions_count:    int
    positions:          list[PositionResponse] = []
