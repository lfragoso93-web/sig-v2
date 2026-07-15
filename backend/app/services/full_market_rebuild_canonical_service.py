"""Ponto de entrada canônico do full market rebuild.

Reutiliza o orquestrador estável e substitui somente a etapa de snapshots pelo
backfill que usa os motores de valuation dedicados.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.services import full_market_rebuild_service as base_rebuild
from app.services.portfolio_snapshot_canonical_twr_service import (
    backfill_canonical_snapshots_with_returns,
)

logger = logging.getLogger(__name__)


async def _rebuild_all_canonical_twr_snapshots() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Portfolio.id)
            .join(Transaction, Transaction.portfolio_id == Portfolio.id)
            .where(Portfolio.is_active.is_(True))
            .distinct()
            .order_by(Portfolio.id.asc())
        )
        portfolio_ids = [row.id for row in rows.all()]

    processed = 0
    snapshots = 0
    errors = 0
    for portfolio_id in portfolio_ids:
        try:
            async with AsyncSessionLocal() as db:
                snapshots += await backfill_canonical_snapshots_with_returns(db, portfolio_id)
            processed += 1
        except Exception:
            errors += 1
            logger.exception(
                "[full_market_rebuild_canonical] falha ao reconstruir TWR portfolio=%s",
                portfolio_id,
            )

    return {
        "portfolios": len(portfolio_ids),
        "processed": processed,
        "errors": errors,
        "snapshots": snapshots,
        "valuation_mode": "canonical",
    }


async def run_full_market_rebuild():
    """Executa o orquestrador existente com a etapa TWR canônica."""
    original = base_rebuild._rebuild_all_twr_snapshots
    base_rebuild._rebuild_all_twr_snapshots = _rebuild_all_canonical_twr_snapshots
    try:
        return await base_rebuild.run_full_market_rebuild()
    finally:
        base_rebuild._rebuild_all_twr_snapshots = original
