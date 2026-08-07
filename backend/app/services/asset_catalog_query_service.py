"""Consultas DB-first ao catálogo persistido de ativos.

Este serviço não consulta providers. O catálogo é abastecido pelo bootstrap
certificado e deve ser a única fonte para descoberta/sugestão no runtime.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType


@dataclass(frozen=True)
class AssetCatalogSuggestion:
    ticker: str
    name: str
    asset_type: str


def _normalize_filter(asset_type: str | None) -> tuple[str, ...] | None:
    if not asset_type:
        return None

    value = asset_type.strip().upper()
    aliases: dict[str, tuple[str, ...]] = {
        "CRIPTO": (AssetType.CRIPTO.value,),
        "STOCK_INT": (AssetType.STOCK.value,),
        "ETF_INT": (AssetType.ETF_INTERNACIONAL.value,),
        "ACAO": (AssetType.ACAO.value,),
        "FII": (AssetType.FII.value,),
        "ETF_NACIONAL": (AssetType.ETF_NACIONAL.value,),
        "BDR": (AssetType.BDR.value,),
        "TESOURO": (AssetType.TESOURO_DIRETO.value,),
        "TESOURO_DIRETO": (AssetType.TESOURO_DIRETO.value,),
        "RENDA_FIXA": (AssetType.RENDA_FIXA.value,),
    }
    return aliases.get(value, (value,))


async def suggest_assets_from_catalog(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 10,
    asset_type: str | None = None,
) -> list[AssetCatalogSuggestion]:
    """Busca ticker/nome exclusivamente no catálogo persistido."""
    normalized = query.strip().upper()
    if not normalized:
        return []

    like = f"%{normalized}%"
    stmt = select(Asset).where(
        or_(
            func.upper(Asset.ticker).like(like),
            func.upper(func.coalesce(Asset.name, "")).like(like),
        )
    )

    allowed_types = _normalize_filter(asset_type)
    if allowed_types:
        stmt = stmt.where(Asset.asset_type.in_(allowed_types))

    stmt = stmt.order_by(
        case((func.upper(Asset.ticker) == normalized, 0), else_=1),
        Asset.ticker,
    ).limit(max(1, min(limit, 50)))

    result = await db.execute(stmt)
    assets = result.scalars().all()
    return [
        AssetCatalogSuggestion(
            ticker=asset.ticker,
            name=asset.name or asset.ticker,
            asset_type=str(asset.asset_type),
        )
        for asset in assets
    ]


async def list_treasury_from_catalog(
    db: AsyncSession,
    query: str = "",
    *,
    limit: int = 200,
) -> list[AssetCatalogSuggestion]:
    """Lista títulos do Tesouro já persistidos pelo bootstrap."""
    stmt = select(Asset).where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
    normalized = query.strip().upper()
    if normalized:
        like = f"%{normalized}%"
        stmt = stmt.where(
            or_(
                func.upper(Asset.ticker).like(like),
                func.upper(func.coalesce(Asset.name, "")).like(like),
            )
        )

    stmt = stmt.order_by(Asset.ticker).limit(max(1, min(limit, 500)))
    result = await db.execute(stmt)
    assets = result.scalars().all()
    return [
        AssetCatalogSuggestion(
            ticker=asset.ticker,
            name=asset.name or asset.ticker,
            asset_type=AssetType.TESOURO_DIRETO.value,
        )
        for asset in assets
    ]
