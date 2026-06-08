from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate
from typing import Optional


async def get_or_create_asset(
    db: AsyncSession, data: AssetCreate
) -> Asset:
    """Busca ativo existente ou cria novo. Chave única: ticker + asset_type."""
    result = await db.execute(
        select(Asset).where(
            Asset.ticker == data.ticker.upper(),
            Asset.asset_type == data.asset_type,
        )
    )
    asset = result.scalar_one_or_none()
    if asset:
        return asset
    asset = Asset(
        ticker=data.ticker.upper(),
        name=data.name,
        asset_type=data.asset_type,
        currency=data.currency,
        brapi_ticker=data.brapi_ticker or data.ticker.upper(),
        sector=data.sector,
        logo_url=data.logo_url,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def search_assets(
    db: AsyncSession,
    query: str,
    asset_type: Optional[AssetType] = None,
    limit: int = 20,
) -> list[Asset]:
    stmt = select(Asset)
    if query:
        like = f"%{query.upper()}%"
        stmt = stmt.where(
            (Asset.ticker.ilike(like)) | (Asset.name.ilike(like))
        )
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    stmt = stmt.order_by(Asset.ticker).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
