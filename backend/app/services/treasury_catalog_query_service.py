"""Consultas DB-first de apresentação do catálogo do Tesouro Direto."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType


async def get_persisted_treasury_commercial_names(
    db: AsyncSession,
    symbols: list[str],
) -> dict[str, str]:
    """Retorna nomes persistidos por símbolo, sem consultar providers."""
    normalized = {
        symbol.strip().lower()
        for symbol in symbols
        if symbol and symbol.strip()
    }
    if not normalized:
        return {}

    result = await db.execute(
        select(Asset.ticker, Asset.name).where(
            Asset.asset_type == AssetType.TESOURO_DIRETO.value,
            func.lower(Asset.ticker).in_(normalized),
        )
    )
    return {
        str(row.ticker).strip().lower(): str(row.name).strip()
        for row in result.all()
        if row.ticker and row.name and str(row.name).strip()
    }
