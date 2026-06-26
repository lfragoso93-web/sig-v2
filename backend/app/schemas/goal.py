from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GoalCreate(BaseModel):
    portfolio_id: int
    name: str
    target_value: float
    current_value: float = 0.0
    target_date: Optional[datetime] = None
    description: Optional[str] = None


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    target_date: Optional[datetime] = None
    description: Optional[str] = None


class GoalResponse(BaseModel):
    id: int
    portfolio_id: int
    name: str
    target_value: float
    current_value: float
    target_date: Optional[datetime] = None
    description: Optional[str] = None
    created_at: datetime
    progress_pct: float
    is_completed: bool

    model_config = {"from_attributes": True}
