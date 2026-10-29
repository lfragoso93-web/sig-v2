"""Serviço de semeadura e sincronização do catálogo de ativos internacionais (Stocks e ETFs)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.models.asset import Asset
from app.services.international_universe_service import (
    fetch_supported_international_universe,
)

logger = logging.getLogger(__name__)


@dataclass
class InternationalCatalogSyncResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    total: int = 0
    errors: int = 0


async def seed_international_catalog(
    db: AsyncSession,
) -> InternationalCatalogSyncResult:
    """Sincroniza o catálogo base de Stocks e ETFs internacionais no banco de dados."""
    universe = await fetch_supported_international_universe(db)
    result = InternationalCatalogSyncResult(total=len(universe))

    logger.info(
        "[international_catalog] Sincronizando catálogo internacional com %d ativos...",
        len(universe),
    )

    for item in universe:
        try:
            # Busca pelo ticker e tipo
            stmt = select(Asset).where(
                Asset.ticker == item.ticker,
                Asset.asset_type == item.asset_type,
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()

            if existing is None:
                new_asset = Asset(
                    ticker=item.ticker,
                    name=item.name,
                    asset_type=item.asset_type,
                    currency=item.currency,
                )
                db.add(new_asset)
                result.created += 1
            else:
                changed = False
                if not existing.name and item.name:
                    existing.name = item.name
                    changed = True
                if existing.currency != "USD":
                    existing.currency = "USD"
                    changed = True

                if changed:
                    result.updated += 1
                else:
                    result.unchanged += 1

        except Exception as exc:
            result.errors += 1
            logger.warning(
                "[international_catalog] Erro ao sincronizar ativo %s: %s",
                sanitize_log_value(item.ticker),
                sanitize_log_value(exc),
            )

    await db.commit()
    logger.info(
        "[international_catalog] Concluído: total=%d created=%d updated=%d unchanged=%d errors=%d",
        result.total,
        result.created,
        result.updated,
        result.unchanged,
        result.errors,
    )
    return result
