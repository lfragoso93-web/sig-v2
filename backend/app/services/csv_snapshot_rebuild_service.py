"""Reconstrucao assincrona de snapshots apos importacao CSV retroativa."""

import logging

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.transaction import Transaction
from app.services.portfolio_service import invalidate_portfolio_cache
from app.services.portfolio_snapshot_service import invalidate_snapshots_from
from app.services.portfolio_snapshot_twr_service import backfill_snapshots_with_returns
from app.services.rentabilidade_service import flush_rentabilidade_cache

logger = logging.getLogger(__name__)


async def rebuild_snapshots_after_csv_import(portfolio_id: int) -> None:
    """Reconstroi o historico diario completo sem bloquear a resposta HTTP."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.min(Transaction.date)).where(
                    Transaction.portfolio_id == portfolio_id
                )
            )
            first_date = result.scalar_one_or_none()
            if first_date is None:
                logger.info(
                    "[csv_snapshot_rebuild] portfolio=%s sem transacoes",
                    portfolio_id,
                )
                return

            removed = await invalidate_snapshots_from(
                db,
                portfolio_id,
                first_date,
                commit=True,
            )
            created = await backfill_snapshots_with_returns(db, portfolio_id)

            await invalidate_portfolio_cache(portfolio_id)
            await flush_rentabilidade_cache(portfolio_id)

            logger.info(
                "[csv_snapshot_rebuild] portfolio=%s inicio=%s removidos=%s criados=%s",
                portfolio_id,
                first_date,
                removed,
                created,
            )
    except Exception:
        logger.exception(
            "[csv_snapshot_rebuild] falha ao reconstruir portfolio=%s",
            portfolio_id,
        )
