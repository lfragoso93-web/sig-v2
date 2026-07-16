"""Manutenção automática dos snapshots enriquecidos de carteiras ativas."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction
from app.services.dividend_aggregation_service import sum_received_dividends
from app.services.portfolio_snapshot_twr_service import backfill_snapshots_with_returns

logger = logging.getLogger(__name__)
_MONEY_TOLERANCE = Decimal("0.01")


async def _portfolio_needs_twr_rebuild(
    db: AsyncSession,
    portfolio_id: int,
) -> bool:
    """Detecta cobertura ausente ou proventos recebidos ainda não refletidos."""
    first_tx_result = await db.execute(
        select(func.min(Transaction.date)).where(
            Transaction.portfolio_id == portfolio_id
        )
    )
    first_date = first_tx_result.scalar_one_or_none()
    if first_date is None:
        return False

    snapshot_result = await db.execute(
        select(
            func.count(PortfolioSnapshot.id),
            func.min(PortfolioSnapshot.snapshot_date),
            func.max(PortfolioSnapshot.snapshot_date),
        ).where(PortfolioSnapshot.portfolio_id == portfolio_id)
    )
    count, min_date, max_date = snapshot_result.one()
    if int(count or 0) == 0:
        return True
    if min_date is None or min_date > first_date:
        return True
    if max_date is None or max_date < date.today():
        return True

    latest_result = await db.execute(
        select(PortfolioSnapshot.dividends_accumulated)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == max_date,
        )
        .limit(1)
    )
    snapshot_dividends = Decimal(str(latest_result.scalar_one_or_none() or 0))
    canonical_dividends = Decimal(
        str(await sum_received_dividends(db, portfolio_id, as_of=max_date))
    )
    return abs(snapshot_dividends - canonical_dividends) > _MONEY_TOLERANCE


async def maintain_twr_snapshots_for_active_portfolios(
    db: AsyncSession,
) -> dict[str, int]:
    """Reconstrói o TWR somente quando cobertura ou proventos estiverem divergentes."""
    result = await db.execute(
        select(Portfolio.id)
        .join(Transaction, Transaction.portfolio_id == Portfolio.id)
        .where(Portfolio.is_active.is_(True))
        .distinct()
    )
    portfolio_ids = [row.id for row in result.all()]

    processed = 0
    skipped = 0
    errors = 0
    snapshots = 0

    for portfolio_id in portfolio_ids:
        try:
            if not await _portfolio_needs_twr_rebuild(db, portfolio_id):
                skipped += 1
                continue
            snapshots += await backfill_snapshots_with_returns(db, portfolio_id)
            processed += 1
        except Exception as exc:
            await db.rollback()
            errors += 1
            logger.exception(
                "[snapshot_twr_auto] portfolio=%s falhou: %s",
                portfolio_id,
                exc,
            )

    return {
        "portfolios": len(portfolio_ids),
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "snapshots": snapshots,
    }
