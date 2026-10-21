from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel

GoalType = Literal["PATRIMONIO", "PROVENTOS", "RENTABILIDADE", "LIVRE"]


class GoalCreate(BaseModel):
    portfolio_id: int
    goal_type: GoalType = "LIVRE"
    name: str
    target_value: float
    # current_value é preenchido automaticamente pelo service para tipos auto;
    # obrigatório apenas para LIVRE
    current_value: float = 0.0
    monthly_contribution: Optional[float] = None  # aporte mensal projetado
    target_date: Optional[date] = None  # pode ser nulo (calculado)
    description: Optional[str] = None
    is_active: bool = True


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    monthly_contribution: Optional[float] = None
    target_date: Optional[date] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class GoalResponse(BaseModel):
    id: int
    portfolio_id: int
    goal_type: str
    name: str
    target_value: float
    current_value: float
    base_value: float
    monthly_contribution: Optional[float]
    target_date: Optional[date]
    description: Optional[str]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # calculados
    progress_pct: float  # 0-100
    is_completed: bool
    months_to_goal: Optional[float]  # meses restantes projetados
    projected_date: Optional[datetime]  # data projetada de conclusão

    model_config = {"from_attributes": True}
