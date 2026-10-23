"""Servico central de autenticacao e seguranca do SGI v2.

Gerencia login com protecao contra forca bruta, Google OAuth 2.0 federado,
autenticacao multi-fator (MFA TOTP) e recuperacao transacional de senhas.
"""

from datetime import timedelta
import logging
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    TokenResponse,
)
from app.schemas.password_policy import validate_strong_password
from app.schemas.user import UserCreate
from app.services.email_service import (
    send_password_changed_email,
    send_password_reset_email,
    send_welcome_email,
)
from app.services.google_oauth_service import (
    create_oauth_state,
    exchange_code_for_user_info,
    get_google_auth_url,
    verify_and_consume_oauth_state,
)
from app.services.lockout_service import (
    check_lockout,
    clear_lockout,
    register_failed_attempt,
)
from app.services.totp_service import (
    generate_backup_codes,
    generate_qr_code_data_uri,
    generate_totp_secret,
    get_totp_uri,
    serialize_backup_codes,
    verify_and_consume_backup_code,
    verify_totp,
)
from app.services.user_service import create_user, get_user_by_email

logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRE_MINUTES = 30
MFA_PENDING_EXPIRE_MINUTES = 5

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais invalidas",
)


async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    """Autentica o usuario por e-mail e senha com lockout e desafio MFA."""
    email_clean = data.email.strip().lower()
    await check_lockout(email_clean)

    user = await get_user_by_email(db, email_clean)
    if not user:
        await register_failed_attempt(email_clean)
        logger.warning("Login falhou: email inexistente (%s)", email_clean)
        raise _INVALID_CREDENTIALS

    try:
        senha_ok = verify_password(data.password, user.hashed_password)
    except Exception as exc:
        await register_failed_attempt(email_clean)
        logger.error("Erro ao verificar senha id=%s: %s", user.id, exc)
        raise _INVALID_CREDENTIALS from exc

    if not senha_ok:
        await register_failed_attempt(email_clean)
        logger.warning("Login falhou: senha incorreta id=%s", user.id)
        raise _INVALID_CREDENTIALS

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o administrador.",
        )

    await clear_lockout(email_clean)

    # Se MFA ativo, emite token temporario para o desafio de 2FA
    if user.totp_enabled and user.totp_secret:
        mfa_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=MFA_PENDING_EXPIRE_MINUTES),
            token_type="mfa_pending",
        )
        return TokenResponse(
            token_type="bearer",
            mfa_required=True,
            mfa_token=mfa_token,
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        token_type="bearer",
        mfa_required=False,
    )


async def verify_mfa_login(
    db: AsyncSession, mfa_token: str, code: str
) -> TokenResponse:
    """Valida o codigo TOTP ou backup code apos credenciais primarias."""
    payload = decode_token(mfa_token)
    if not payload or payload.get("type") != "mfa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao de verificacao MFA expirada ou invalida.",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado ou inativo.",
        )

    clean_code = code.strip()
    is_valid = False

    # 1. Tenta validar via TOTP 6 digitos
    if user.totp_secret and verify_totp(user.totp_secret, clean_code):
        is_valid = True
    else:
        # 2. Tenta validar e consumir codigo de backup
        backup_valid, updated_codes = verify_and_consume_backup_code(
            user.totp_backup_codes, clean_code
        )
        if backup_valid:
            is_valid = True
            user.totp_backup_codes = updated_codes
            await db.flush()

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Codigo de autenticacao invalido.",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        token_type="bearer",
        mfa_required=False,
    )


async def setup_mfa(user: User) -> MfaSetupResponse:
    """Gera um segredo TOTP e codigos de recuperacao para configuracao."""
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    uri = get_totp_uri(secret, user.email)
    qr_code = generate_qr_code_data_uri(uri)
    return MfaSetupResponse(
        secret=secret,
        uri=uri,
        qr_code=qr_code,
        backup_codes=backup_codes,
    )


async def enable_mfa(
    db: AsyncSession, user: User, data: MfaEnableRequest
) -> bool:
    """Ativa o MFA apos confirmacao de codigo TOTP gerado com o segredo."""
    if not verify_totp(data.secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo incorreto. Verifique o relogio do seu dispositivo.",
        )

    user.totp_secret = data.secret
    user.totp_backup_codes = serialize_backup_codes(data.backup_codes)
    user.totp_enabled = True
    await db.flush()
    return True


async def disable_mfa(db: AsyncSession, user: User, code: str) -> bool:
    """Desativa o MFA mediante confirmacao de codigo TOTP ou backup."""
    if not user.totp_enabled:
        return True

    clean_code = code.strip()
    is_valid = False
    if user.totp_secret and verify_totp(user.totp_secret, clean_code):
        is_valid = True
    else:
        backup_valid, _ = verify_and_consume_backup_code(
            user.totp_backup_codes, clean_code
        )
        if backup_valid:
            is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo invalido. Nao foi possivel desativar o MFA.",
        )

    user.totp_secret = None
    user.totp_backup_codes = None
    user.totp_enabled = False
    await db.flush()
    return True


def get_mfa_status(user: User) -> MfaStatusResponse:
    """Retorna o status atual de MFA e o provedor de autenticacao."""
    return MfaStatusResponse(
        mfa_enabled=bool(user.totp_enabled),
        auth_provider=user.auth_provider or "local",
    )


async def register_user(db: AsyncSession, data: UserCreate) -> TokenResponse:
    """Cadastra usuario, despacha boas-vindas e retorna tokens de sessao."""
    user = await create_user(db, data)
    try:
        await send_welcome_email(user.email, user.name)
    except Exception as exc:
        logger.warning("Falha ao enviar email de boas-vindas: %s", exc)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        token_type="bearer",
        mfa_required=False,
    )


async def get_google_login_url() -> tuple[str, bool]:
    """Gera URL de autorizacao Google OAuth 2.0 protegida por state CSRF."""
    if not settings.GOOGLE_CLIENT_ID:
        return "", False
    state = await create_oauth_state()
    url = get_google_auth_url(state)
    return url, True


async def handle_google_callback(
    db: AsyncSession, code: str, state: str
) -> TokenResponse:
    """Processa retorno do Google, autentica ou cria conta federada."""
    state_valid = await verify_and_consume_oauth_state(state)
    if not state_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requisicao OAuth invalida ou expirada (CSRF state).",
        )

    user_info = await exchange_code_for_user_info(code)
    email = user_info.get("email", "").strip().lower()
    google_sub = str(user_info.get("sub", ""))

    if not email or not google_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perfil do Google incompleto. E-mail nao fornecido.",
        )

    # Busca por sub do Google ou por email
    stmt = select(User).where(
        (User.google_sub == google_sub) | (User.email == email)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        if not user.google_sub:
            user.google_sub = google_sub
            if user.auth_provider == "local":
                user.auth_provider = "google"
        picture = user_info.get("picture")
        if picture and not user.avatar_url:
            user.avatar_url = picture
        await db.flush()
    else:
        # Cria novo usuario vinculado ao Google
        name = user_info.get("name") or email.split("@")[0]
        picture = user_info.get("picture")
        random_pwd = hash_password(secrets.token_urlsafe(32))
        user = User(
            name=name,
            email=email,
            hashed_password=random_pwd,
            role=UserRole.user,
            is_active=True,
            auth_provider="google",
            google_sub=google_sub,
            avatar_url=picture,
            onboarding_completed=False,
        )
        db.add(user)
        await db.flush()
        try:
            await send_welcome_email(user.email, user.name)
        except Exception as exc:
            logger.warning("Falha ao enviar email boas-vindas Google: %s", exc)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o administrador.",
        )

    if user.totp_enabled and user.totp_secret:
        mfa_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=MFA_PENDING_EXPIRE_MINUTES),
            token_type="mfa_pending",
        )
        return TokenResponse(
            token_type="bearer",
            mfa_required=True,
            mfa_token=mfa_token,
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        token_type="bearer",
        mfa_required=False,
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
    """Gera novo access_token a partir de refresh_token valido."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado",
        )
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado ou inativo",
        )
    return create_access_token(str(user.id))


async def forgot_password(db: AsyncSession, email: str) -> str:
    """Gera token de recuperacao e dispara e-mail via Brevo/SMTP."""
    user = await get_user_by_email(db, email.strip().lower())
    if not user or not user.is_active:
        return "usuario-nao-encontrado-token-invalido"

    reset_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        token_type="reset",
    )
    try:
        await send_password_reset_email(user.email, reset_token)
    except Exception as exc:
        logger.error(
            "Erro ao enviar email de reset para usuario id=%s: %s",
            user.id,
            exc,
        )
    return reset_token


async def reset_password(
    db: AsyncSession, token: str, new_password: str
) -> None:
    """Valida token e atualiza senha cumprindo a politica de seguranca."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )
    try:
        validate_strong_password(new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(hashed_password=hash_password(new_password))
    )
    await db.flush()
    try:
        await send_password_changed_email(
            user.email,
            user.name or user.email,
            origin="recuperação por link de e-mail",
        )
    except Exception as exc:
        logger.warning(
            "Falha ao enviar aviso de senha redefinida id=%s: %s",
            user.id,
            exc,
        )
