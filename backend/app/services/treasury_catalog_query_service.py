"""Consultas DB-first de apresentação do catálogo do Tesouro Direto."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.treasury_instrument import TreasuryInstrument


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
        select(
            Asset.ticker,
            TreasuryInstrument.commercial_name,
            Asset.name.label("legacy_name"),
        )
        .outerjoin(
            TreasuryInstrument,
            TreasuryInstrument.asset_id == Asset.id,
        )
        .where(
            Asset.asset_type == AssetType.TESOURO_DIRETO.value,
            func.lower(Asset.ticker).in_(normalized),
        )
    )
    names: dict[str, str] = {}
    for row in result.all():
        name = row.commercial_name or row.legacy_name
        if row.ticker and name and str(name).strip():
            names[str(row.ticker).strip().lower()] = str(name).strip()
    return names
