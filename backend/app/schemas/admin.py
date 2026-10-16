from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.models.admin_backup_operation import (
    BackupOperationStatus,
    BackupOperationType,
)


class AdminRestoreRequest(BaseModel):
    backup_filename: str = Field(min_length=1, max_length=255)
    current_password: str = Field(min_length=1, max_length=128)


class AdminBackupOperationResponse(BaseModel):
    id: UUID
    operation_type: BackupOperationType
    status: BackupOperationStatus
    backup_filename: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AdminBackupOperationsResponse(BaseModel):
    operations: list[AdminBackupOperationResponse]
    count: int
