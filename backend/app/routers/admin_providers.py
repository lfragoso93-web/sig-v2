"""Endpoints para gestão dinâmica de provedores pelo SuperAdmin."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.routers.admin import require_superadmin
from app.schemas.provider_config import (
    ProviderConfigResponse,
    ProviderConfigUpdate,
    ProviderTestResponse,
)
from app.services.provider_config_service import ProviderConfigService

router = APIRouter(prefix="/admin/providers", tags=["admin-providers"])


@router.get("", response_model=list[ProviderConfigResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
) -> list[ProviderConfigResponse]:
    """Lista provedores registrados e suas configurações mascaradas."""
    return await ProviderConfigService.list_providers(db)


@router.put("/{provider_id}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider_id: str,
    data: ProviderConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
) -> ProviderConfigResponse:
    """Atualiza de forma auditada e segura configurações de um provedor."""
    try:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        return await ProviderConfigService.update_provider_config(
            provider_id=provider_id,
            data=data,
            user_id=current_user.id,
            db=db,
            ip_address=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connectivity(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
) -> ProviderTestResponse:
    """Executa probe de conectividade ativo sem afetar transações."""
    try:
        return await ProviderConfigService.test_provider_connectivity(
            provider_id, db
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/{provider_id}/reset", response_model=ProviderConfigResponse)
async def reset_provider_config(
    provider_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
) -> ProviderConfigResponse:
    """Restaura a configuração do provedor para os padrões do sistema."""
    try:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        return await ProviderConfigService.reset_provider_to_default(
            provider_id=provider_id,
            user_id=current_user.id,
            db=db,
            ip_address=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
