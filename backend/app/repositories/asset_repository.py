"""Asset catalog queries encapsulated in a dedicated repository."""

from __future__ import annotations

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


async def get_asset_by_id(db: AsyncSession, asset_id: int) -> Asset | None:
    """Busca ativo por ID primario."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    return result.scalar_one_or_none()


async def get_asset_by_ticker(db: AsyncSession, ticker: str) -> Asset | None:
    """Busca ativo por ticker normalizado."""
    clean_ticker = ticker.upper().strip()
    result = await db.execute(select(Asset).where(Asset.ticker == clean_ticker))
    return result.scalar_one_or_none()


async def get_assets_by_tickers(
    db: AsyncSession,
    tickers: Sequence[str],
) -> Sequence[Asset]:
    """Busca múltiplos ativos por lista de tickers normalizados."""
    normalized = [t.upper().strip() for t in tickers if t]
    if not normalized:
        return []
    result = await db.execute(select(Asset).where(Asset.ticker.in_(normalized)))
    return result.scalars().all()
