from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import re
from sqlalchemy import and_, func, select, or_
from app.models.asset import Asset, AssetType
from app.models.asset_alias import AssetAlias
from app.schemas.asset import AssetCreate


async def get_or_create_asset(
    db: AsyncSession,
    data: AssetCreate,
) -> tuple[Asset, bool]:
    """
    Retorna (asset, is_new).

    A identidade canônica do catálogo é (ticker, asset_type), alinhada ao
    constraint uq_asset_ticker_type do modelo. A criação básica do catálogo é
    local. Nenhum caller deve usar is_new para disparar onboarding ou ingestão
    externa automática; catálogo completo, metadados e históricos pertencem
    ao bootstrap certificado do ambiente.
    """
    raw_ticker = data.ticker.strip()
    asset_type = (
        data.asset_type.value
        if isinstance(data.asset_type, AssetType)
        else str(data.asset_type).strip().upper()
    )
    ticker = (
        raw_ticker.lower()
        if asset_type == AssetType.TESOURO_DIRETO.value
        else raw_ticker.upper()
    )

    result = await db.execute(
        select(Asset).where(
            func.lower(Asset.ticker) == ticker.lower(),
            Asset.asset_type == asset_type,
        )
    )
    asset = result.scalar_one_or_none()
    if asset:
        return asset, False

    alias_result = await db.execute(
        select(Asset)
        .join(AssetAlias, AssetAlias.asset_id == Asset.id)
        .where(
            func.lower(AssetAlias.alias_ticker) == ticker.lower(),
            AssetAlias.asset_type == asset_type,
        )
    )
    aliased_asset = alias_result.scalar_one_or_none()
    if aliased_asset:
        return aliased_asset, False

    asset = Asset(
        ticker=ticker,
        name=data.name,
        asset_type=asset_type,
        currency=getattr(data, "currency", None) or "BRL",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset, True


async def list_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(select(Asset).order_by(Asset.ticker))
    return list(result.scalars().all())


async def get_asset_by_ticker(db: AsyncSession, ticker: str) -> Asset | None:
    norm_ticker = ticker.strip()
    result = await db.execute(
        select(Asset).where(func.lower(Asset.ticker) == norm_ticker.lower())
    )
    asset = result.scalar_one_or_none()
    if asset:
        return asset

    alias_result = await db.execute(
        select(Asset)
        .join(AssetAlias, AssetAlias.asset_id == Asset.id)
        .where(func.lower(AssetAlias.alias_ticker) == norm_ticker.lower())
    )
    return alias_result.scalar_one_or_none()


_B3_CLASS_TYPES = frozenset({
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
})
_B3_TICKER_DIGITS_RE = re.compile(r"^[A-Z][A-Z0-9]*\d+[A-Z]?$")


async def search_assets(
    db: AsyncSession,
    q: str,
    asset_type: Optional[AssetType] = None,
    limit: int = 20,
) -> list[Asset]:
    """Busca ativos por ticker, nome ou alias historico, com filtro estrito de asset_type."""
    from app.services.asset_catalog_query_service import _user_selectable_catalog_predicate

    asset_type_val = asset_type.value if asset_type is not None else None
    alias_join = (
        and_(AssetAlias.asset_id == Asset.id, AssetAlias.asset_type == asset_type_val)
        if asset_type_val is not None
        else (AssetAlias.asset_id == Asset.id)
    )
    query = (
        select(Asset)
        .outerjoin(AssetAlias, alias_join)
        .where(_user_selectable_catalog_predicate())
    )
    if q.strip():
        like = f"%{q.strip().upper()}%"
        query = query.where(
            or_(
                Asset.ticker.ilike(like),
                Asset.name.ilike(like),
                AssetAlias.alias_ticker.ilike(like),
            )
        )
    if asset_type_val is not None:
        query = query.where(Asset.asset_type == asset_type_val)
    query = query.distinct().order_by(Asset.ticker).limit(limit)
    result = await db.execute(query)
    assets = list(result.scalars().all())
    if asset_type_val in _B3_CLASS_TYPES:
        assets = [
            a
            for a in assets
            if _B3_TICKER_DIGITS_RE.fullmatch(str(a.ticker or "").strip().upper())
        ]
    return assets
