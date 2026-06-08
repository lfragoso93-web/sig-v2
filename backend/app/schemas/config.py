from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SystemConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    description: Optional[str] = None
    is_public: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemConfigUpdate(BaseModel):
    value: str


class SystemConfigBulkUpdate(BaseModel):
    configs: dict[str, str]  # {key: value}
