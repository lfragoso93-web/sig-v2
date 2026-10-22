"""Testes para google_oauth_service (Issue #97)."""

import pytest
from app.services.google_oauth_service import (
    create_oauth_state,
    get_google_auth_url,
    verify_and_consume_oauth_state,
)
from app.core.config import settings


@pytest.mark.asyncio
async def test_oauth_state_generation_and_consumption():
    state = await create_oauth_state()
    assert isinstance(state, str)
    assert len(state) >= 16

    # Valida e consome state
    valid = await verify_and_consume_oauth_state(state)
    assert valid is True

    # Reutilizacao deve ser rejeitada
    reused = await verify_and_consume_oauth_state(state)
    assert reused is False


def test_get_google_auth_url():
    settings.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    settings.GOOGLE_REDIRECT_URI = "https://sgi.com/auth/callback"
    url = get_google_auth_url("test-state-token")

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-client-id.apps.googleusercontent.com" in url
    assert "redirect_uri=https%3A%2F%2Fsgi.com%2Fauth%2Fcallback" in url
    assert "state=test-state-token" in url
