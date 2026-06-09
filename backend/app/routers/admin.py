from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserAdminUpdate
from app.schemas.auth import MessageResponse
from app.schemas.config import SystemConfigResponse, SystemConfigUpdate, SystemConfigBulkUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.user_service import (
    create_user, list_users, get_user_by_id,
    admin_update_user, delete_user, count_users
)
from app.services.config_service import get_all_configs, update_config, bulk_update_configs
import math

router = APIRouter()


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a SuperAdmins",
        )
    return current_user


# ── Gestão de Usuários ───────────────────────────────────────────────

@router.get("/users", response_model=PaginatedResponse[UserListResponse])
async def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todos os usuários com paginação e busca."""
    users, total = await list_users(db, page, page_size, search)
    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    data: UserCreate,
    role: UserRole = Query(UserRole.user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Cria usuário (SuperAdmin pode definir role)."""
    return await create_user(db, data, role=role)


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def admin_update_user_endpoint(
    user_id: int,
    data: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Edita qualquer campo do usuário incluindo role e status."""
    if user_id == current_user.id and data.role and data.role != UserRole.superadmin:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio SuperAdmin")
    return await admin_update_user(db, user_id, data)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Remove usuário permanentemente (cascade deleta carteiras e dados)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta")
    await delete_user(db, user_id)
    return MessageResponse(message="Usuário excluído com sucesso")


@router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
async def admin_toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Ativa ou desativa um usuário."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = not user.is_active
    await db.flush()
    await db.refresh(user)
    return user


# ── Estatísticas do sistema ───────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Estatísticas gerais do sistema para o painel admin."""
    total_users = await count_users(db)
    return {
        "total_users": total_users,
        "version": "2.0.0",
        "system": "SGI — Sistema de Gestão de Investimentos",
    }


# ── Configurações do sistema ──────────────────────────────────

@router.get("/config", response_model=list[SystemConfigResponse])
async def admin_list_configs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todas as configurações do sistema (incluindo privadas)."""
    return await get_all_configs(db, public_only=False)


@router.put("/config/{key}", response_model=SystemConfigResponse)
async def admin_update_config(
    key: str,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Atualiza uma configuração do sistema."""
    return await update_config(db, key, data.value)


@router.put("/config", response_model=list[SystemConfigResponse])
async def admin_bulk_update_config(
    data: SystemConfigBulkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Atualiza múltiplas configurações de uma vez."""
    return await bulk_update_configs(db, data.configs)
