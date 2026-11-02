from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import UserRole
from app.routers.admin import router


def _client_for(role: UserRole) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/admin")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=71, role=role
    )
    app.dependency_overrides[get_db] = lambda: SimpleNamespace(commit=AsyncMock())
    return TestClient(app)


def test_superadmin_can_unlock_user_and_operation_is_audited():
    target = SimpleNamespace(id=18, email="locked@example.com")
    with (
        patch("app.routers.admin.get_user_by_id", new=AsyncMock(return_value=target)),
        patch("app.routers.admin.admin_unlock_lockout", new=AsyncMock()) as unlock_login,
        patch(
            "app.routers.admin.clear_password_reset_lockout", new=AsyncMock()
        ) as unlock_reset,
        patch("app.routers.admin.AuditLogService.log_action", new=AsyncMock()) as audit,
    ):
        response = _client_for(UserRole.superadmin).post("/api/v1/admin/users/18/unlock")

    assert response.status_code == 200
    assert response.json()["message"] == "Bloqueios do usuário removidos com sucesso."
    unlock_login.assert_awaited_once_with(target.email)
    unlock_reset.assert_awaited_once_with(target.email)
    assert audit.await_args.kwargs["user_id"] == 71
    assert audit.await_args.kwargs["resource_id"] == 18
    assert audit.await_args.kwargs["new_values"] == {"event": "unlocked_by_superadmin"}


def test_non_superadmin_cannot_unlock_user():
    with patch("app.routers.admin.admin_unlock_lockout", new=AsyncMock()) as unlock_login:
        response = _client_for(UserRole.user).post("/api/v1/admin/users/18/unlock")

    assert response.status_code == 403
    unlock_login.assert_not_awaited()
