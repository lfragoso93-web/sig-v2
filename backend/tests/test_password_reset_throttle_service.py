from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import password_reset_throttle_service as throttle
from app.services import auth_service


@pytest.mark.asyncio
async def test_two_requests_are_allowed_and_third_locks_account_for_one_hour():
    email = "two-minute-reset-limit@example.com"
    with patch.object(throttle, "get_redis", new=AsyncMock(return_value=None)):
        await throttle.clear_password_reset_lockout(email)
        await throttle.register_password_reset_request(email)
        await throttle.register_password_reset_request(email)

        with pytest.raises(HTTPException) as exc_info:
            await throttle.register_password_reset_request(email)

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["Retry-After"] == str(throttle.LOCKOUT_SECONDS)

        with pytest.raises(HTTPException) as locked:
            await throttle.register_password_reset_request(email)
        assert locked.value.status_code == 429

        await throttle.clear_password_reset_lockout(email)
        await throttle.register_password_reset_request(email)


@pytest.mark.asyncio
async def test_redis_counter_uses_atomic_script_and_account_scoped_keys():
    redis_client = AsyncMock()
    redis_client.eval.return_value = (1, 0)
    email = "redis-reset-limit@example.com"

    with patch.object(throttle, "get_redis", new=AsyncMock(return_value=redis_client)):
        await throttle.register_password_reset_request(email)

    args = redis_client.eval.await_args.args
    assert args[1] == 3
    assert args[2].endswith(":window")
    assert args[3].endswith(":lock")
    assert args[4].endswith(":sequence")
    assert args[5:] == (throttle.WINDOW_SECONDS, throttle.MAX_REQUESTS, throttle.LOCKOUT_SECONDS)
    assert email not in " ".join(str(arg) for arg in args)


@pytest.mark.asyncio
async def test_production_fails_closed_when_redis_is_unavailable(monkeypatch):
    monkeypatch.setattr(throttle.settings, "ENVIRONMENT", "production")
    with patch.object(throttle, "get_redis", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await throttle.register_password_reset_request("redis-down@example.com")

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_forgot_password_applies_account_limit_before_sending_email():
    email = "reset-flow-throttle@example.com"
    user = SimpleNamespace(id=804, email=email, is_active=True)
    with (
        patch.object(auth_service, "get_user_by_email", new=AsyncMock(return_value=user)),
        patch.object(
            auth_service, "register_password_reset_request", new=AsyncMock()
        ) as register_limit,
        patch.object(auth_service.AuditLogService, "log_action", new=AsyncMock()),
        patch.object(auth_service, "send_password_reset_email", new=AsyncMock()) as send_email,
    ):
        await auth_service.forgot_password(AsyncMock(), email)

    register_limit.assert_awaited_once_with(email)
    send_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_account_does_not_consume_reset_limit_or_send_email():
    with (
        patch.object(auth_service, "get_user_by_email", new=AsyncMock(return_value=None)),
        patch.object(
            auth_service, "register_password_reset_request", new=AsyncMock()
        ) as register_limit,
        patch.object(auth_service, "send_password_reset_email", new=AsyncMock()) as send_email,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.forgot_password(AsyncMock(), "not-a-user@example.com")

    assert exc_info.value.status_code == 404
    register_limit.assert_not_awaited()
    send_email.assert_not_awaited()
