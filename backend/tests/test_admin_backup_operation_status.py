from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.models.admin_backup_operation import BackupOperationStatus
from app.models.admin_backup_operation import (
    AdminBackupOperation,
    BackupOperationType,
)
from app.services import backup_service


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return False


@pytest.mark.asyncio
async def test_operation_model_persists_uuid_and_enum_values(db, user) -> None:
    operation = AdminBackupOperation(
        operation_type=BackupOperationType.BACKUP,
        status=BackupOperationStatus.QUEUED,
        requested_by_user_id=user.id,
    )
    db.add(operation)
    await db.commit()

    persisted = await db.get(AdminBackupOperation, operation.id)

    assert persisted is not None
    assert persisted.operation_type is BackupOperationType.BACKUP
    assert persisted.status is BackupOperationStatus.QUEUED


@pytest.mark.asyncio
async def test_backup_operation_persists_running_then_succeeded() -> None:
    operation_id = uuid4()
    operation = SimpleNamespace(
        status=BackupOperationStatus.QUEUED,
        started_at=None,
        finished_at=None,
        error_message="stale",
    )
    session = AsyncMock()
    session.get.return_value = operation
    result = {"success": True, "backup_id": "backup-id", "size_mb": 1.2}

    with (
        patch.object(backup_service, "AsyncSessionLocal", return_value=_SessionContext(session)),
        patch.object(
            backup_service, "create_database_backup", new=AsyncMock(return_value=result)
        ),
        patch.object(backup_service, "_utc_now", side_effect=["started", "finished"]),
    ):
        await backup_service.run_database_backup_operation(operation_id, "safe-db-url")

    assert operation.status == BackupOperationStatus.SUCCEEDED
    assert operation.started_at == "started"
    assert operation.finished_at == "finished"
    assert operation.error_message is None
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_failed_backup_persists_generic_error_without_service_details() -> None:
    operation_id = uuid4()
    operation = SimpleNamespace(
        status=BackupOperationStatus.QUEUED,
        started_at=None,
        finished_at=None,
        error_message=None,
    )
    session = AsyncMock()
    session.get.return_value = operation
    result = {"success": False, "error": "password leaked by upstream"}

    with (
        patch.object(backup_service, "AsyncSessionLocal", return_value=_SessionContext(session)),
        patch.object(
            backup_service, "create_database_backup", new=AsyncMock(return_value=result)
        ),
        patch.object(backup_service, "_utc_now", side_effect=["started", "finished"]),
    ):
        await backup_service.run_database_backup_operation(operation_id, "safe-db-url")

    assert operation.status == BackupOperationStatus.FAILED
    assert operation.finished_at == "finished"
    assert operation.error_message == "Backup failed"
    assert "password" not in operation.error_message
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_restore_persists_running_before_restore_execution() -> None:
    operation_id = uuid4()
    operation = SimpleNamespace(
        status=BackupOperationStatus.QUEUED,
        started_at=None,
        finished_at=None,
        error_message=None,
    )
    session = AsyncMock()
    session.get.return_value = operation
    restore = AsyncMock(return_value={"success": True})
    timeline = []
    restore.side_effect = lambda *_args: timeline.append(
        (operation.status, session.commit.await_count)
    ) or {"success": True}

    with (
        patch.object(backup_service, "AsyncSessionLocal", return_value=_SessionContext(session)),
        patch.object(backup_service, "restore_database_backup", new=restore),
        patch.object(backup_service, "_utc_now", return_value="started"),
    ):
        await backup_service.run_database_restore_operation(
            operation_id, "safe-db-url", "backup_20261016_120000.sql.gz"
        )

    assert timeline == [(BackupOperationStatus.RUNNING, 1)]
