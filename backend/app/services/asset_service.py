from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.asset import Asset
from app.schemas.asset import AssetCreate


async def get_or_create_asset(db: AsyncSession, data: AssetCreate) -> Asset:
    result = await db.execute(select(Asset).where(Asset.ticker == data.ticker))
    asset = result.scalar_one_or_none()
    if asset:
        return asset
    asset = Asset(
        ticker=data.ticker,
        name=data.name,
        asset_type=data.asset_type,
        currency=getattr(data, "currency", "BRL"),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def list_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(select(Asset).order_by(Asset.ticker))
    return list(result.scalars().all())


async def get_asset_by_ticker(db: AsyncSession, ticker: str) -> Asset | None:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    return result.scalar_one_or_none()
