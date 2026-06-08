from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset import AssetType
from app.schemas.asset import AssetCreate, AssetResponse
from app.services.asset_service import get_or_create_asset, search_assets
from typing import Optional

router = APIRouter()


@router.get("/search", response_model=list[AssetResponse])
async def search_assets_endpoint(
    q: str = Query("", min_length=1),
    asset_type: Optional[AssetType] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Busca ativos por ticker ou nome."""
    return await search_assets(db, q, asset_type, limit)


@router.post("/", response_model=AssetResponse)
async def upsert_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Cria ou retorna ativo existente (ticker + tipo é único)."""
    return await get_or_create_asset(db, data)
