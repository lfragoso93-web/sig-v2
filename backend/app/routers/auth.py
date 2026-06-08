from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse, MessageResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import login, refresh_access_token
from app.services.user_service import create_user, is_registration_allowed
from app.core.security import create_access_token
from fastapi import HTTPException

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Registro público de novo usuário. Respeita config allow_registration."""
    if not await is_registration_allowed(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registro de novos usuários está desativado. Contate o administrador.",
        )
    user = await create_user(db, data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Autentica usuário e retorna access + refresh token."""
    return await login(db, data)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_endpoint(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Renova o access token usando um refresh token válido."""
    access_token = await refresh_access_token(db, data.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
):
    """Retorna dados do usuário autenticado."""
    return current_user
