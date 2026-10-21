from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RebalanceAction(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    REDUCE = "reduce"


class ConcentrationRiskLevel(str, Enum):
    LOW = "low"
    BALANCED = "balanced"
    WARNING = "warning"
    CRITICAL = "critical"


class TopAssetConcentration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    name: str | None = None
    current_value: float
    weight_in_class_pct: float
    weight_in_portfolio_pct: float


class ClassAllocationAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_value: float
    current_weight_pct: float
    target_weight_pct: float | None = None
    target_value: float | None = None
    gap_weight_pct: float | None = None
    gap_value: float | None = None
    rebalance_action: RebalanceAction
    suggested_action_label: str


class ClassConcentrationAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_count: int
    top_asset: TopAssetConcentration | None = None
    hhi_score: float | None = None
    risk_level: ConcentrationRiskLevel
    risk_label: str
    status_message: str


class ClassIncomeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_applicable: bool
    total_proventos: float
    weighted_dy_pct: float | None = None
    top_income_asset: str | None = None
    status_label: str


class ClassFixedIncomeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_applicable: bool
    cdi_allocation_pct: float | None = None
    ipca_allocation_pct: float | None = None
    pre_allocation_pct: float | None = None
    maturing_next_12m_value: float | None = None
    maturing_next_12m_pct: float | None = None


class ClassAnalysisDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: str
    label: str
    health_score: int = Field(ge=0, le=100)
    allocation: ClassAllocationAnalysis
    concentration: ClassConcentrationAnalysis
    income: ClassIncomeAnalysis
    fixed_income: ClassFixedIncomeAnalysis
    key_findings: list[str] = Field(default_factory=list)


class PortfolioConsolidatedAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: int
    portfolio_name: str
    reference_date: str
    total_value: float
    overall_health_score: int = Field(ge=0, le=100)
    max_divergence_class: str | None = None
    classes_analyzed_count: int
    rebalance_priority_classes: list[str] = Field(default_factory=list)
    classes: list[ClassAnalysisDetail]
    provenance: dict[str, str] = Field(default_factory=dict)
