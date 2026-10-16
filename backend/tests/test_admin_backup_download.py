from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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


def test_superadmin_can_download_backup(tmp_path: Path) -> None:
    backup = tmp_path / "backup_20261013_120000.sql.gz"
    backup.write_bytes(b"compressed-backup")

    with patch(
        "app.services.backup_service.get_backup_download_path",
        return_value=backup,
    ):
        response = _client_for(UserRole.superadmin).get(
            f"/api/v1/admin/database/backups/{backup.name}",
        )

    assert response.status_code == 200
    assert response.content == b"compressed-backup"
    assert response.headers["content-type"] == "application/gzip"
    assert f'filename="{backup.name}"' in response.headers["content-disposition"]


def test_non_superadmin_cannot_download_backup() -> None:
    response = _client_for(UserRole.user).get(
        "/api/v1/admin/database/backups/backup_20261013_120000.sql.gz",
    )

    assert response.status_code == 403


def test_download_rejects_invalid_backup_filename() -> None:
    with patch(
        "app.services.backup_service.get_backup_download_path",
        side_effect=ValueError("Invalid backup filename"),
    ):
        response = _client_for(UserRole.superadmin).get(
            "/api/v1/admin/database/backups/not-a-backup.sql.gz",
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Nome de backup inválido"}


def test_download_returns_not_found_for_missing_backup() -> None:
    with patch(
        "app.services.backup_service.get_backup_download_path",
        return_value=None,
    ):
        response = _client_for(UserRole.superadmin).get(
            "/api/v1/admin/database/backups/backup_20261013_120000.sql.gz",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Backup não encontrado"}
