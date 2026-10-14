from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.core.deps import get_current_user
from app.models.user import UserRole
from app.routers.admin import router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client_for(role: UserRole) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/admin")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=role)
    return TestClient(app)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/admin/database/backup"),
        ("get", "/api/v1/admin/database/backups"),
        (
            "post",
            "/api/v1/admin/database/restore"
            "?backup_filename=backup_20261014_120000.sql.gz",
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

    with patch("app.routers.admin._run_database_backup_bg") as background:
        response = _client_for(UserRole.superadmin).post(
            "/api/v1/admin/database/backup",
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    background.assert_called_once_with("postgresql://database.example/sgi")


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

    with (
        patch(
            "app.services.backup_service.list_backups",
            new=AsyncMock(return_value={"backups": [{"filename": filename}]}),
        ) as list_backups,
        patch(
            "app.services.backup_service.restore_database_backup",
            new=AsyncMock(return_value={"success": True}),
        ) as restore_backup,
    ):
        response = _client_for(UserRole.superadmin).post(
            "/api/v1/admin/database/restore",
            params={"backup_filename": filename},
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["backup_filename"] == filename
    list_backups.assert_awaited_once_with()
    restore_backup.assert_awaited_once_with(database_url, filename)


def test_superadmin_can_delete_backup() -> None:
    filename = "backup_20261014_120000.sql.gz"

    with patch(
        "app.services.backup_service.delete_backup",
        new=AsyncMock(
            return_value={
                "success": True,
                "backup_id": "backup_20261014_120000",
            }
        ),
    ) as delete_backup:
        response = _client_for(UserRole.superadmin).delete(
            f"/api/v1/admin/database/backups/{filename}",
        )

    assert response.status_code == 200
    assert response.json()["backup_id"] == "backup_20261014_120000"
    delete_backup.assert_awaited_once_with(filename)
