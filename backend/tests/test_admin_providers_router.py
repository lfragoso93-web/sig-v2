"""Testes de contrato HTTP dos endpoints de provedores (Issue #127)."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import UserRole
from app.routers.admin_providers import router as admin_providers_router
from app.schemas.provider_config import (
    ProviderConfigResponse,
    ProviderTestResponse,
)


def _client_for(role: UserRole) -> TestClient:
    app = FastAPI()
    db = AsyncMock()
    db.add = Mock()
    app.state.db = db
    app.include_router(admin_providers_router, prefix="/api/v1")
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
        ("get", "/api/v1/admin/providers"),
        ("put", "/api/v1/admin/providers/brapi"),
        ("post", "/api/v1/admin/providers/brapi/test"),
        ("post", "/api/v1/admin/providers/brapi/reset"),
    ],
)
def test_provider_endpoints_reject_non_superadmin(
    method: str, path: str
) -> None:
    """Garante que usuários com role 'user' são rejeitados com 403."""
    client = _client_for(UserRole.user)
    kwargs = {}
    if method == "put":
        kwargs["json"] = {"priority": 5}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


def test_list_providers_authorized_for_superadmin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SuperAdmin lista provedores com contratos e segredos mascarados."""
    client = _client_for(UserRole.superadmin)

    fake_response = [
        ProviderConfigResponse(
            provider_id="brapi",
            display_name="BRAPI",
            description="Cotações e proventos",
            capabilities=["quotes_intraday", "dividends"],
            is_enabled=True,
            priority=5,
            base_url="https://brapi.dev",
            effective_base_url="https://brapi.dev",
            timeout_seconds=15,
            rate_limit_per_minute=300,
            status="OK",
            requires_auth=True,
            has_api_key_configured=True,
            api_key_masked="br_****7f",
            is_official_authority=False,
            is_customized=False,
        )
    ]

    async def _mock_list(_db):
        return fake_response

    from app.services.provider_config_service import ProviderConfigService

    monkeypatch.setattr(ProviderConfigService, "list_providers", _mock_list)

    response = client.get("/api/v1/admin/providers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["provider_id"] == "brapi"
    assert data[0]["has_api_key_configured"] is True
    assert data[0]["api_key_masked"] == "br_****7f"


def test_update_provider_authorized_for_superadmin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SuperAdmin consegue atualizar parâmetros dinâmicos de provedor."""
    client = _client_for(UserRole.superadmin)

    fake_updated = ProviderConfigResponse(
        provider_id="brapi",
        display_name="BRAPI",
        description="Cotações e proventos",
        capabilities=["quotes_intraday", "dividends"],
        is_enabled=True,
        priority=2,
        base_url="https://custom.brapi.dev",
        effective_base_url="https://custom.brapi.dev",
        timeout_seconds=20,
        rate_limit_per_minute=400,
        status="OK",
        requires_auth=True,
        has_api_key_configured=True,
        api_key_masked="my_****xyz",
        is_official_authority=False,
        is_customized=True,
    )

    async def _mock_update(
        provider_id, data, user_id, db, ip_address=None, user_agent=None
    ):
        return fake_updated

    from app.services.provider_config_service import ProviderConfigService

    monkeypatch.setattr(
        ProviderConfigService, "update_provider_config", _mock_update
    )

    response = client.put(
        "/api/v1/admin/providers/brapi",
        json={
            "priority": 2,
            "base_url": "https://custom.brapi.dev",
            "timeout_seconds": 20,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == 2
    assert data["base_url"] == "https://custom.brapi.dev"
    assert data["is_customized"] is True


def test_probe_endpoint_authorized_for_superadmin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SuperAdmin consegue disparar teste de probe ativo."""
    client = _client_for(UserRole.superadmin)

    fake_probe = ProviderTestResponse(
        provider_id="brapi",
        success=True,
        status="OK",
        latency_ms=120.5,
        message="Conexão OK",
        tested_at=datetime.now(timezone.utc),
    )

    async def _mock_test(provider_id, db):
        return fake_probe

    from app.services.provider_config_service import ProviderConfigService

    monkeypatch.setattr(
        ProviderConfigService, "test_provider_connectivity", _mock_test
    )

    response = client.post("/api/v1/admin/providers/brapi/test")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "OK"
    assert data["latency_ms"] == 120.5
