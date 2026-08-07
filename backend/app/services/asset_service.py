from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate


async def get_or_create_asset(
    db: AsyncSession,
    data: AssetCreate,
) -> tuple[Asset, bool]:
    """
    Retorna (asset, is_new).

    A criação básica do catálogo é local. Nenhum caller deve usar `is_new` para
    disparar onboarding ou ingestão externa automática; catálogo completo,
    metadados e históricos pertencem ao bootstrap certificado do ambiente.
    """
    result = await db.execute(select(Asset).where(Asset.ticker == data.ticker))
    asset = result.scalar_one_or_none()
    if asset:
        return asset, False

    asset = Asset(
        ticker=data.ticker,
        name=data.name,
        asset_type=data.asset_type,
        currency=getattr(data, "currency", "BRL"),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset, True


async def list_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(select(Asset).order_by(Asset.ticker))
    return list(result.scalars().all())


async def get_asset_by_ticker(db: AsyncSession, ticker: str) -> Asset | None:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    return result.scalar_one_or_none()


async def search_assets(
    db: AsyncSession,
    q: str,
    asset_type: Optional[AssetType] = None,
    limit: int = 20,
) -> list[Asset]:
    """Busca ativos por ticker ou nome, com filtro opcional de asset_type."""
    query = select(Asset)
    if q.strip():
        like = f"%{q.strip().upper()}%"
        query = query.where(
            or_(
                Asset.ticker.ilike(like),
                Asset.name.ilike(like),
            )
        )
    if asset_type is not None:
        query = query.where(Asset.asset_type == asset_type)
    query = query.order_by(Asset.ticker).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
