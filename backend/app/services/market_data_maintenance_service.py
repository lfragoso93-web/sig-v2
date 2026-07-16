"""Manutencao conservadora da base canonica apos o rebuild.

A rotina remove somente registros objetivamente invalidos ou impossiveis. Ela
nao tenta deduplicar entidades por heuristica nem apagar historico valido.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.provider_status import normalize_provider_status
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot

logger = logging.getLogger(__name__)


async def run_market_data_maintenance(db: AsyncSession) -> dict[str, int]:
    """Limpa anomalias seguras e normaliza estados legados de provedor."""
    today = date.today()
    now = datetime.now(timezone.utc)

    invalid_prices_result = await db.execute(
        delete(AssetPrice).where(
            (AssetPrice.close <= 0)
            | (AssetPrice.timestamp > now)
        )
    )
    invalid_prices_removed = int(invalid_prices_result.rowcount or 0)

    future_snapshots_result = await db.execute(
        delete(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date > today)
    )
    future_snapshots_removed = int(future_snapshots_result.rowcount or 0)

    orphan_price_count = int(
        (
            await db.execute(
                select(func.count(AssetPrice.id))
                .outerjoin(Asset, Asset.id == AssetPrice.asset_id)
                .where(Asset.id.is_(None))
            )
        ).scalar_one()
        or 0
    )
    orphan_snapshot_count = int(
        (
            await db.execute(
                select(func.count(PortfolioSnapshot.id))
                .outerjoin(Portfolio, Portfolio.id == PortfolioSnapshot.portfolio_id)
                .where(Portfolio.id.is_(None))
            )
        ).scalar_one()
        or 0
    )

    assets_result = await db.execute(
        select(Asset).where(Asset.provider_status.is_not(None))
    )
    provider_status_normalized = 0
    for asset in assets_result.scalars().all():
        normalized = normalize_provider_status(asset.provider_status).value
        if asset.provider_status != normalized:
            asset.provider_status = normalized
            provider_status_normalized += 1

    await db.commit()
    result = {
        "invalid_prices_removed": invalid_prices_removed,
        "future_snapshots_removed": future_snapshots_removed,
        "orphan_prices_detected": orphan_price_count,
        "orphan_snapshots_detected": orphan_snapshot_count,
        "provider_status_normalized": provider_status_normalized,
    }
    logger.info("[market_maintenance] concluido resultado=%s", result)
    return result
