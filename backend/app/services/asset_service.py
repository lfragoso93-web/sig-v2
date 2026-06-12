import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi import fetch_logo_url
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate

logger = logging.getLogger(__name__)

# Tipos que suportam busca de logo via BRAPI (nacionais)
_BRAPI_LOGO_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
}


async def _resolve_logo(ticker: str, asset_type: AssetType, provided: Optional[str]) -> Optional[str]:
    """
    Retorna logo_url: usa o valor fornecido se existir,
    caso contrario tenta buscar via BRAPI (apenas para tipos nacionais).
    Silencioso em caso de falha.
    """
    if provided:
        return provided
    if asset_type not in _BRAPI_LOGO_TYPES:
        return None
    try:
        return await fetch_logo_url(ticker)
    except Exception as e:
        logger.warning("_resolve_logo: falha ao buscar logo para %s: %s", ticker, e)
        return None


async def get_or_create_asset(
    db: AsyncSession, data: AssetCreate
) -> Asset:
    """Busca ativo existente ou cria novo. Chave unica: ticker + asset_type."""
    result = await db.execute(
        select(Asset).where(
            Asset.ticker == data.ticker.upper(),
            Asset.asset_type == data.asset_type,
        )
    )
    asset = result.scalar_one_or_none()

    if asset:
        # Atualiza logo se ainda nao tiver
        if not asset.logo_url:
            asset.logo_url = await _resolve_logo(
                asset.brapi_ticker or asset.ticker,
                asset.asset_type,
                data.logo_url,
            )
            await db.flush()
        return asset

    # Cria novo ativo
    logo = await _resolve_logo(
        data.ticker.upper(),
        data.asset_type,
        data.logo_url,
    )

    asset = Asset(
        ticker=data.ticker.upper(),
        name=data.name,
        asset_type=data.asset_type,
        currency=data.currency,
        brapi_ticker=data.brapi_ticker or data.ticker.upper(),
        sector=data.sector,
        logo_url=logo,
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
