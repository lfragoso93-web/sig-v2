"""Schemas para correlação de ativo com carteira e insights de IA (Issue #58)."""

from typing import Any, Optional
from pydantic import BaseModel


class AssetPortfolioPositionInsight(BaseModel):
    is_held: bool
    quantity: float = 0.0
    average_price: float = 0.0
    invested_value: float = 0.0
    current_price: float = 0.0
    current_value: float = 0.0
    capital_gain_value: float = 0.0
    capital_gain_percent: float = 0.0
    dividends_received: float = 0.0
    total_return_value: float = 0.0
    total_return_percent: float = 0.0
    portfolio_weight_percent: float = 0.0
    class_weight_percent: float = 0.0
    class_name: Optional[str] = None
    class_label: Optional[str] = None
    class_current_allocation_percent: float = 0.0
    class_target_percent: Optional[float] = None
    yield_on_cost_percent: Optional[float] = None


class AIAssetInsight(BaseModel):
    concentration_level: str  # "LOW", "BALANCED", "WARNING", "HIGH"
    concentration_message: str
    income_assessment: str
    rebalancing_guidance: str
    strategic_role: str
    explainable_summary: str


class AssetPortfolioInsightResponse(BaseModel):
    ticker: str
    portfolio_id: int
    position: AssetPortfolioPositionInsight
    enrichment: dict[str, Any]
    ai_insights: AIAssetInsight
