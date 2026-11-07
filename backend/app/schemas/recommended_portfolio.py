from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RecommendedAsset(BaseModel):
    ticker: str
    name: str
    asset_type: str
    current_price: float
    target_weight_pct: float
    reason: str
    expected_yield_pct: Optional[float] = None
    risk_level: str = "moderate"


class RecommendedClass(BaseModel):
    asset_type: str
    label: str
    target_weight_pct: float
    description: str
    assets: list[RecommendedAsset] = Field(default_factory=list)


class RecommendedPortfolio(BaseModel):
    id: str
    title: str
    subtitle: str
    strategy: str  # 'patrimonio' | 'proventos' | 'performance'
    thesis: str
    risk_profile: str  # 'Conservador', 'Moderado', 'Arrojado'
    expected_annual_return: str
    expected_dividend_yield: str
    suggested_time_horizon: str
    diversification_score: int  # 0-100
    classes: list[RecommendedClass] = Field(default_factory=list)


class SimulatedAssetAllocation(BaseModel):
    ticker: str
    name: str
    asset_type: str
    current_price: float
    weight_in_portfolio_pct: float
    allocated_amount: float
    suggested_quantity: float
    reason: str


class SimulatedClassAllocation(BaseModel):
    asset_type: str
    label: str
    target_weight_pct: float
    allocated_amount: float
    assets: list[SimulatedAssetAllocation] = Field(default_factory=list)


class RecommendedPortfolioSimulationRequest(BaseModel):
    strategy: str = "patrimonio"
    total_amount: float = Field(gt=0, description="Valor monetário a ser aportado")
    custom_class_weights: Optional[dict[str, float]] = None


class RecommendedPortfolioSimulationResponse(BaseModel):
    strategy: str
    total_amount: float
    classes: list[SimulatedClassAllocation] = Field(default_factory=list)
    summary: str
