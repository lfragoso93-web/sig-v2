"""Rotas de autenticacao, seguranca, OAuth e MFA do SGI v2."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import get_client_ip, limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.token_blacklist import (
    blacklist_token,
    is_blacklisted,
    is_user_session_revoked,
)
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleCallbackRequest,
    GoogleOAuthUrlResponse,
    LoginRequest,
    MessageResponse,
    MfaDisableRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserCreate
from app.services import auth_service
from app.services.user_service import get_user_by_id

router = APIRouter(tags=["auth"])


def _extract_request_metadata(
    request: Request,
) -> tuple[str | None, str | None]:
    """Extrai IP real e User-Agent da requisicao para trilha de auditoria."""
    try:
        ip_address = get_client_ip(request)
    except Exception:
        ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    if user_agent:
        user_agent = user_agent[:500]
    return ip_address, user_agent


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Autenticacao por e-mail e senha com lockout e suporte a MFA."""
    return await auth_service.login(db, data)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.REGISTER_RATE_LIMIT)
async def register(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cadastro publico com envio de e-mail de boas-vindas."""
    return await auth_service.register_user(db, data)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit(settings.FORGOT_PASSWORD_RATE_LIMIT)
async def request_password_reset(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Responde de forma uniforme e envia o link em background quando elegivel."""
    ip_address, user_agent = _extract_request_metadata(request)
    reset_token = await auth_service.forgot_password(
        db,
        data.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()
    if reset_token:
        background_tasks.add_task(
            auth_service.send_password_reset_email_safely,
            data.email,
            reset_token,
        )
    return ForgotPasswordResponse(
        message="Se houver uma conta ativa para este e-mail, enviaremos instrucoes de recuperacao.",
        reset_token=None,
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(settings.RESET_PASSWORD_RATE_LIMIT)
async def confirm_password_reset(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Redefine a senha usando token de recuperacao valido e de uso unico."""
    ip_address, user_agent = _extract_request_metadata(request)
    await auth_service.reset_password(
        db,
        data.token,
        data.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()
    return MessageResponse(message="Senha redefinida com sucesso")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Troca um refresh token valido por um novo par access + refresh."""
    payload = decode_token(data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado.",
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token sem jti — faca login novamente.",
        )

    if await is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token ja utilizado ou revogado.",
        )

    user_id = int(payload["sub"])
    if await is_user_session_revoked(user_id, payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao revogada por alteracao de senha. Faca login novamente.",
        )

    await blacklist_token(jti, payload["exp"])

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado ou inativo.",
        )

    new_access = create_access_token(subject=payload["sub"])
    new_refresh = create_refresh_token(subject=payload["sub"])
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        mfa_required=False,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest):
    """Revoga o refresh token enviado."""
    payload = decode_token(data.refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti")
        if jti:
            await blacklist_token(jti, payload["exp"])


# ── Google OAuth 2.0 (Issue #97) ──────────────────────────────────────────


@router.get("/google/url", response_model=GoogleOAuthUrlResponse)
async def get_google_oauth_url():
    """Retorna URL de autorizacao Google com protecao anti-CSRF."""
    url, enabled = await auth_service.get_google_login_url()
    return GoogleOAuthUrlResponse(url=url, enabled=enabled)


@router.post("/google/callback", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def google_callback(
    request: Request,
    data: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Troca authorization code por sessao autenticada no SGI v2."""
    tokens = await auth_service.handle_google_callback(
        db, data.code, data.state
    )
    await db.commit()
    return tokens


# ── Autenticacao Multi-Fator (MFA TOTP) ───────────────────────────────────


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    current_user: User = Depends(get_current_user),
):
    """Gera segredo TOTP e codigos descartaveis para habilitacao do MFA."""
    return await auth_service.setup_mfa(current_user)


@router.post("/mfa/enable", response_model=MessageResponse)
async def mfa_enable(
    data: MfaEnableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ativa o segundo fator de autenticacao com validacao de codigo."""
    await auth_service.enable_mfa(db, current_user, data)
    await db.commit()
    return MessageResponse(
        message="Autenticacao de dois fatores ativada com sucesso."
    )


@router.post("/mfa/disable", response_model=MessageResponse)
async def mfa_disable(
    data: MfaDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desativa o MFA com confirmacao de codigo de seguranca."""
    await auth_service.disable_mfa(db, current_user, data.code)
    await db.commit()
    return MessageResponse(
        message="Autenticacao de dois fatores desativada com sucesso."
    )


@router.get("/mfa/status", response_model=MfaStatusResponse)
async def mfa_status(
    current_user: User = Depends(get_current_user),
):
    """Informa se o usuario possui MFA ativado e o provedor de autenticacao."""
    return auth_service.get_mfa_status(current_user)


@router.post("/mfa/verify", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def mfa_verify(
    request: Request,
    data: MfaVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Conclui o login verificando o codigo TOTP ou codigo de backup."""
    tokens = await auth_service.verify_mfa_login(
        db, data.mfa_token, data.code
    )
    await db.commit()
    return tokens
