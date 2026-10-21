from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AiExplanationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    is_mock_or_deterministic: bool = True
    execution_time_ms: float = 0.0
    disclaimer: str = (
        "Análise gerada por inteligência artificial baseada estritamente nas métricas "
        "determinísticas calculadas da carteira. Não constitui recomendação de investimento."
    )


class ContributionScenarioDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float
    description: str
    priority_class: str
    estimated_gap_reduction: str


class PortfolioAiAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: int
    portfolio_name: str
    reference_date: str
    overall_health_score: int = Field(ge=0, le=100)
    posture_label: str
    posture_summary: str
    executive_summary: str
    key_strengths: list[str] = Field(default_factory=list)
    attention_points: list[str] = Field(default_factory=list)
    rebalancing_strategy: str
    contribution_scenarios: list[ContributionScenarioDto] = Field(default_factory=list)
    metadata: AiExplanationMetadata


class ContributionSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contribution_amount: float = Field(gt=0, description="Valor do aporte em reais (BRL)")


class ClassContributionAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: str
    label: str
    current_value: float
    current_weight_pct: float
    target_weight_pct: float | None = None
    allocated_amount: float
    projected_value: float
    projected_weight_pct: float
    action_explanation: str


class ContributionSimulationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: int
    contribution_amount: float
    current_total_value: float
    projected_total_value: float
    suggested_allocations: list[ClassContributionAllocation]
    overall_impact_summary: str
    metadata: AiExplanationMetadata


class AiQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500)
    context_preset: str | None = None


class AiQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: int
    question: str
    answer: str
    key_metrics_referenced: list[str] = Field(default_factory=list)
    metadata: AiExplanationMetadata
