from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, Dict
from app.models.audit_log import AuditAction


class AuditLogCreate(BaseModel):
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    portfolio_id: Optional[int] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "SUCCESS"
    error_message: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    resource_type: str
    resource_id: Optional[int]
    portfolio_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogDetailResponse(AuditLogResponse):
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    changes: Optional[Dict[str, Any]]


class AuditLogFilterParams(BaseModel):
    page: int = 1
    page_size: int = 50
    user_id: Optional[int] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    portfolio_id: Optional[int] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None


class PaginatedAuditLogs(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditStatsResponse(BaseModel):
    total_logs: int
    logs_today: int
    logs_this_week: int
    actions_breakdown: Dict[str, int]
    resource_types_breakdown: Dict[str, int]
    failed_operations: int


class UserAuditStatsResponse(BaseModel):
    user_id: int
    total_actions: int
    actions_breakdown: Dict[str, int]
    last_action: Optional[datetime]
    failed_actions: int


class AuditLogCleanupResponse(BaseModel):
    deleted_count: int
    freed_space_mb: float
