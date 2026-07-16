"""Atualização de cotações com invalidação dos consumidores afetados."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete
from app.models.asset import AssetType
from app.models.transaction import Transaction


async def invalidate_quote_consumers(
    db: AsyncSession,
    asset_types: list[AssetType] | None = None,
) -> int:
    """Remove caches de Resumo e posições das carteiras afetadas pelo lote."""
    query = select(Transaction.portfolio_id).distinct()
    if asset_types:
        query = query.where(
            Transaction.asset_type.in_([asset_type.value for asset_type in asset_types])
        )
    portfolio_ids = [row.portfolio_id for row in (await db.execute(query)).all()]
    for portfolio_id in portfolio_ids:
        await cache_delete(f"portfolio:{portfolio_id}:summary")
        await cache_delete(f"portfolio:{portfolio_id}:positions")
    return len(portfolio_ids)


async def refresh_quotes_and_invalidate(
    db: AsyncSession,
    asset_types: list[AssetType] | None = None,
) -> tuple[int, int]:
    """Atualiza preços, persiste o lote e invalida caches dependentes."""
    from app.services.quotes_service import update_all_quotes

    updated = await update_all_quotes(db, asset_types=asset_types)
    invalidated = await invalidate_quote_consumers(db, asset_types=asset_types)
    return updated, invalidated
