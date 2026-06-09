from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    AccessTokenResponse,
    MessageResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import (
    login,
    refresh_access_token,
    forgot_password,
    reset_password,
)
from app.services.user_service import create_user, is_registration_allowed, count_users
from app.core.security import create_access_token
from app.models.user import UserRole
from fastapi import HTTPException

router = APIRouter()


@router.post("/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def setup_admin(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria o primeiro admin do sistema. So funciona se nao houver nenhum usuario cadastrado."""
    total = await count_users(db)
    if total > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup ja realizado. Este endpoint so funciona com banco vazio.",
        )
    user = await create_user(db, data, role=UserRole.superadmin)
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Registro publico de novo usuario. Respeita config allow_registration."""
    if not await is_registration_allowed(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registro de novos usuarios esta desativado. Contate o administrador.",
        )
    user = await create_user(db, data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Autentica usuario e retorna access + refresh token."""
    return await login(db, data)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_endpoint(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Renova o access token usando um refresh token valido."""
    access_token = await refresh_access_token(db, data.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
):
    """Retorna dados do usuario autenticado."""
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password_endpoint(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Solicita reset de senha.
    Retorna um token valido por 30 minutos.
    Em producao com SMTP, substituir por envio de e-mail.
    """
    token = await forgot_password(db, data.email)
    return ForgotPasswordResponse(
        message="Se o e-mail estiver cadastrado, voce recebeu as instrucoes de recuperacao.",
        reset_token=token,
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password_endpoint(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Redefine a senha usando o token de reset."""
    await reset_password(db, data.token, data.new_password)
    return MessageResponse(message="Senha redefinida com sucesso. Faca login com a nova senha.")
