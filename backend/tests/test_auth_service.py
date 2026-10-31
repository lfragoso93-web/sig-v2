"""Testes para auth_service — senhas, tokens, MFA, Google OAuth e reset."""

from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.token_blacklist import is_user_session_revoked
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MfaEnableRequest,
)
from app.services import auth_service
from app.services.totp_service import (
    compute_totp,
    generate_backup_codes,
    generate_totp_secret,
    serialize_backup_codes,
)


class TestPasswordHash:

    def test_hash_diferente_do_plain(self):
        plain = "senha123"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_senha_correta(self):
        plain = "senha123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_senha_errada(self):
        hashed = hash_password("correta")
        assert verify_password("errada", hashed) is False

    def test_hash_deterministico_falso(self):
        plain = "senha"
        assert hash_password(plain) != hash_password(plain)

    def test_verify_string_vazia(self):
        hashed = hash_password("abc")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:

    def test_token_decodificavel(self):
        token = create_access_token(subject="42")
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "42"
        assert "jti" in payload
        assert "iat_ts" in payload

    def test_token_contem_exp(self):
        token = create_access_token(subject="1")
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "exp" in payload

    def test_token_distinto_para_dados_distintos(self):
        t1 = create_access_token(subject="1")
        t2 = create_access_token(subject="2")
        assert t1 != t2


class TestAuthMfaAndOAuthFlows:

    @pytest.mark.asyncio
    async def test_login_success_without_mfa(self, db: AsyncSession):
        user = User(
            name="Usuario Sem MFA",
            email="sem_mfa@sgi.com",
            hashed_password=hash_password("SenhaForte@123"),
            is_active=True,
            totp_enabled=False,
        )
        db.add(user)
        await db.flush()

        resp = await auth_service.login(
            db,
            LoginRequest(email="sem_mfa@sgi.com", password="SenhaForte@123"),
        )
        assert resp.mfa_required is False
        assert resp.access_token is not None
        assert resp.refresh_token is not None

    @pytest.mark.asyncio
    async def test_login_with_mfa_triggers_challenge_and_verification(
        self, db: AsyncSession
    ):
        secret = generate_totp_secret()
        backup_codes = generate_backup_codes(4)
        user = User(
            name="Usuario Com MFA",
            email="com_mfa@sgi.com",
            hashed_password=hash_password("SenhaForte@123"),
            is_active=True,
            totp_secret=secret,
            totp_enabled=True,
            totp_backup_codes=serialize_backup_codes(backup_codes),
        )
        db.add(user)
        await db.flush()

        # Login primario retorna desafio MFA
        login_resp = await auth_service.login(
            db,
            LoginRequest(email="com_mfa@sgi.com", password="SenhaForte@123"),
        )
        assert login_resp.mfa_required is True
        assert login_resp.mfa_token is not None
        assert login_resp.access_token is None

        # Desafio MFA com TOTP
        totp_code = compute_totp(secret)
        verify_resp = await auth_service.verify_mfa_login(
            db, login_resp.mfa_token, totp_code
        )
        assert verify_resp.mfa_required is False
        assert verify_resp.access_token is not None

        # Desafio MFA com codigo de backup
        login_resp2 = await auth_service.login(
            db,
            LoginRequest(email="com_mfa@sgi.com", password="SenhaForte@123"),
        )
        used_code = backup_codes[0]
        backup_resp = await auth_service.verify_mfa_login(
            db, login_resp2.mfa_token, used_code
        )
        assert backup_resp.access_token is not None

        # Codigo de backup consumido nao funciona na segunda vez
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.verify_mfa_login(
                db, login_resp2.mfa_token, used_code
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_setup_and_enable_mfa(self, db: AsyncSession):
        user = User(
            name="Usuario Setup",
            email="setup_mfa@sgi.com",
            hashed_password=hash_password("SenhaForte@123"),
            is_active=True,
            role=UserRole.superadmin,
        )
        db.add(user)
        await db.flush()

        # Superadmin sem MFA deve receber mfa_recommended=True
        initial_status = auth_service.get_mfa_status(user)
        assert initial_status.mfa_enabled is False
        assert initial_status.mfa_recommended is True

        setup_data = await auth_service.setup_mfa(user)
        assert len(setup_data.secret) == 32
        assert len(setup_data.backup_codes) == 8

        # Codigo correto ativa MFA
        valid_code = compute_totp(setup_data.secret)
        req = MfaEnableRequest(
            secret=setup_data.secret,
            code=valid_code,
            backup_codes=setup_data.backup_codes,
        )
        ok = await auth_service.enable_mfa(db, user, req)
        assert ok is True
        assert user.totp_enabled is True
        assert auth_service.get_mfa_status(user).mfa_recommended is False

        # Desativa MFA
        code_to_disable = compute_totp(setup_data.secret)
        disabled_ok = await auth_service.disable_mfa(
            db, user, code_to_disable
        )
        assert disabled_ok is True
        assert user.totp_enabled is False

    @pytest.mark.asyncio
    async def test_forgot_and_reset_password_flow(self, db: AsyncSession):
        user = User(
            name="Usuario Reset",
            email="reset_flow@sgi.com",
            hashed_password=hash_password("AntigaSenha@123"),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        old_refresh = create_refresh_token(str(user.id))
        old_payload = decode_token(old_refresh)
        assert old_payload is not None
        assert await is_user_session_revoked(user.id, old_payload) is False

        token = await auth_service.forgot_password(
            db,
            "reset_flow@sgi.com",
            ip_address="203.0.113.10",
            user_agent="pytest-agent",
        )
        assert token is not None

        await auth_service.reset_password(
            db,
            token,
            "NovaSenha@98765",
            ip_address="203.0.113.10",
            user_agent="pytest-agent",
        )
        await db.refresh(user)
        assert verify_password("NovaSenha@98765", user.hashed_password) is True

        # Sessao anterior deve estar revogada apos redefinicao de senha
        assert await is_user_session_revoked(user.id, old_payload) is True

        # Nova sessao emitida apos o reset nao deve estar revogada
        new_refresh = create_refresh_token(str(user.id))
        new_payload = decode_token(new_refresh)
        assert new_payload is not None
        assert await is_user_session_revoked(user.id, new_payload) is False

        # Reutilizacao do mesmo token de reset deve ser bloqueada (single-use)
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.reset_password(
                db, token, "OutraSenha@98765"
            )
        assert exc_info.value.status_code == 400
        assert "utilizado" in exc_info.value.detail

        # Deve ter registrado eventos na trilha audit_logs
        logs_res = await db.execute(
            select(AuditLog).where(AuditLog.user_id == user.id)
        )
        logs = list(logs_res.scalars().all())
        resource_types = {log.resource_type for log in logs}
        assert "PasswordResetRequest" in resource_types
        assert "UserPassword" in resource_types

    @pytest.mark.asyncio
    async def test_forgot_password_returns_same_outcome_for_nonexistent_user(
        self, db: AsyncSession
    ):
        with patch(
            "app.services.auth_service.send_password_reset_email",
            new_callable=AsyncMock,
        ) as mock_send:
            result = await auth_service.forgot_password(
                db, "nao_existe_jamais@sgi.com"
            )
            assert result is None
            mock_send.assert_not_awaited()
