from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import UserRole
from app.routers.admin import router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client_for(role: UserRole) -> TestClient:
    app = FastAPI()
    db = AsyncMock()
    app.state.db = db
    app.include_router(router, prefix="/api/v1/admin")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        role=role,
        hashed_password="stored-hash",
    )
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/admin/database/backup"),
        ("get", "/api/v1/admin/database/backups"),
        (
            "post",
            "/api/v1/admin/database/restore",
        ),
        (
            "delete",
            "/api/v1/admin/database/backups/backup_20261014_120000.sql.gz",
        ),
    ],
)
def test_backup_endpoints_reject_non_superadmin(method: str, path: str) -> None:
    response = getattr(_client_for(UserRole.user), method)(path)

    assert response.status_code == 403


def test_superadmin_can_request_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://database.example/sgi")
    client = _client_for(UserRole.superadmin)

    with (
        patch("app.routers.admin._run_database_backup_bg") as background,
        patch(
            "app.routers.admin.AuditLogService.log_action",
            new=AsyncMock(return_value=SimpleNamespace()),
        ) as audit_action,
    ):
        response = client.post(
            "/api/v1/admin/database/backup",
            headers={"user-agent": "admin-console"},
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    background.assert_called_once_with("postgresql://database.example/sgi")
    audit_kwargs = audit_action.await_args.kwargs
    assert audit_kwargs["user_id"] == 1
    assert audit_kwargs["action"] == "BACKUP"
    assert audit_kwargs["resource_type"] == "DatabaseBackup"
    assert audit_kwargs["new_values"] == {"request_status": "accepted"}
    assert audit_kwargs["ip_address"] == "testclient"
    assert audit_kwargs["user_agent"] == "admin-console"
    client.app.state.db.commit.assert_awaited_once()


def test_superadmin_can_list_backups() -> None:
    payload = {
        "backups": [
            {
                "filename": "backup_20261014_120000.sql.gz",
                "size_bytes": 42,
            }
        ]
    }

    with patch(
        "app.services.backup_service.list_backups",
        new=AsyncMock(return_value=payload),
    ) as list_backups:
        response = _client_for(UserRole.superadmin).get(
            "/api/v1/admin/database/backups",
        )

    assert response.status_code == 200
    assert response.json() == payload
    list_backups.assert_awaited_once_with()


def test_superadmin_can_request_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    filename = "backup_20261014_120000.sql.gz"
    database_url = "postgresql://database.example/sgi"
    monkeypatch.setenv("DATABASE_URL", database_url)
    client = _client_for(UserRole.superadmin)

    with (
        patch(
            "app.routers.admin.verify_password",
            return_value=True,
        ) as verify_password,
        patch(
            "app.services.backup_service.list_backups",
            new=AsyncMock(return_value={"backups": [{"filename": filename}]}),
        ) as list_backups,
        patch(
            "app.services.backup_service.restore_database_backup",
            new=AsyncMock(return_value={"success": True}),
        ) as restore_backup,
        patch(
            "app.routers.admin.AuditLogService.log_action",
            new=AsyncMock(return_value=SimpleNamespace()),
        ) as audit_action,
    ):
        response = client.post(
            "/api/v1/admin/database/restore",
            json={
                "backup_filename": filename,
                "current_password": "ValidPass1!",
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["backup_filename"] == filename
    verify_password.assert_called_once_with("ValidPass1!", "stored-hash")
    list_backups.assert_awaited_once_with()
    restore_backup.assert_awaited_once_with(database_url, filename)
    audit_kwargs = audit_action.await_args.kwargs
    assert audit_kwargs["action"] == "RESTORE"
    assert audit_kwargs["new_values"] == {
        "backup_filename": filename,
        "request_status": "accepted",
    }
    assert "current_password" not in audit_kwargs["new_values"]
    client.app.state.db.commit.assert_awaited_once()


def test_restore_rejects_incorrect_current_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://database.example/sgi")

    with (
        patch(
            "app.routers.admin.verify_password",
            return_value=False,
        ),
        patch(
            "app.services.backup_service.list_backups",
            new=AsyncMock(),
        ) as list_backups,
        patch(
            "app.services.backup_service.restore_database_backup",
            new=AsyncMock(),
        ) as restore,
    ):
        response = _client_for(UserRole.superadmin).post(
            "/api/v1/admin/database/restore",
            json={
                "backup_filename": "backup_20261014_120000.sql.gz",
                "current_password": "incorrect",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Credenciais inválidas"}
    list_backups.assert_not_awaited()
    restore.assert_not_awaited()


def test_restore_requires_current_password() -> None:
    response = _client_for(UserRole.superadmin).post(
        "/api/v1/admin/database/restore",
        json={"backup_filename": "backup_20261014_120000.sql.gz"},
    )

    assert response.status_code == 422


def test_superadmin_can_delete_backup() -> None:
    filename = "backup_20261014_120000.sql.gz"
    client = _client_for(UserRole.superadmin)
    audit_log = SimpleNamespace(
        status="REQUESTED",
        error_message=None,
        new_values={"backup_filename": filename, "operation_status": "requested"},
    )

    with (
        patch(
            "app.services.backup_service.delete_backup",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "backup_id": "backup_20261014_120000",
                }
            ),
        ) as delete_backup,
        patch(
            "app.routers.admin.AuditLogService.log_action",
            new=AsyncMock(return_value=audit_log),
        ) as audit_action,
    ):
        response = client.delete(
            f"/api/v1/admin/database/backups/{filename}",
        )

    assert response.status_code == 200
    assert response.json()["backup_id"] == "backup_20261014_120000"
    delete_backup.assert_awaited_once_with(filename)
    audit_kwargs = audit_action.await_args.kwargs
    assert audit_kwargs["action"] == "DELETE"
    assert audit_kwargs["new_values"]["operation_status"] == "requested"
    assert audit_log.status == "SUCCESS"
    assert audit_log.new_values["operation_status"] == "completed"
    assert client.app.state.db.commit.await_count == 2


def test_failed_backup_delete_is_audited_without_exposing_service_error() -> None:
    filename = "backup_20261014_120000.sql.gz"
    client = _client_for(UserRole.superadmin)
    audit_log = SimpleNamespace(
        status="REQUESTED",
        error_message=None,
        new_values={"backup_filename": filename, "operation_status": "requested"},
    )

    with (
        patch(
            "app.services.backup_service.delete_backup",
            new=AsyncMock(
                return_value={
                    "success": False,
                    "error": "Permission denied: C:/private/backups/secret.sql.gz",
                }
            ),
        ),
        patch(
            "app.routers.admin.AuditLogService.log_action",
            new=AsyncMock(return_value=audit_log),
        ),
    ):
        response = client.delete(
            f"/api/v1/admin/database/backups/{filename}",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Não foi possível remover o backup"}
    assert "private" not in response.text
    assert audit_log.status == "FAILURE"
    assert audit_log.error_message == "Backup deletion failed"
    assert client.app.state.db.commit.await_count == 2
