from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

GoalType = Literal["PATRIMONIO", "PROVENTOS", "RENTABILIDADE", "LIVRE"]


class GoalCreate(BaseModel):
    portfolio_id:         int
    goal_type:            GoalType = "LIVRE"
    name:                 str
    target_value:         float
    # current_value é preenchido automaticamente pelo service para tipos auto;
    # obrigatório apenas para LIVRE
    current_value:        float = 0.0
    monthly_contribution: Optional[float] = None  # aporte mensal projetado
    target_date:          Optional[datetime] = None  # pode ser nulo (calculado)
    description:          Optional[str] = None


class GoalUpdate(BaseModel):
    name:                 Optional[str]   = None
    target_value:         Optional[float] = None
    current_value:        Optional[float] = None
    monthly_contribution: Optional[float] = None
    target_date:          Optional[datetime] = None
    description:          Optional[str] = None


class GoalResponse(BaseModel):
    id:                   int
    portfolio_id:         int
    goal_type:            str
    name:                 str
    target_value:         float
    current_value:        float
    base_value:           float
    monthly_contribution: Optional[float]
    target_date:          Optional[datetime]
    description:          Optional[str]
    created_at:           datetime

    # calculados
    progress_pct:         float   # 0-100
    is_completed:         bool
    months_to_goal:       Optional[float]    # meses restantes projetados
    projected_date:       Optional[datetime]  # data projetada de conclusão

    model_config = {"from_attributes": True}
