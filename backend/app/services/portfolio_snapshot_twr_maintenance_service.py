"""Manutenção automática dos snapshots enriquecidos consolidados e por classe."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction
from app.services.dividend_aggregation_service import sum_received_dividends
from app.services.portfolio_class_snapshot_service import (
    SUPPORTED_CLASS_TWR_TYPES,
    rebuild_class_snapshots,
)
from app.services.portfolio_snapshot_twr_service import backfill_snapshots_with_returns

logger = logging.getLogger(__name__)
_MONEY_TOLERANCE = Decimal("0.01")


async def _portfolio_needs_twr_rebuild(db: AsyncSession, portfolio_id: int) -> bool:
    first_tx_result = await db.execute(
        select(func.min(Transaction.date)).where(Transaction.portfolio_id == portfolio_id)
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
    if int(count or 0) == 0 or min_date is None or min_date > first_date:
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


async def _portfolio_needs_class_twr_rebuild(db: AsyncSession, portfolio_id: int) -> bool:
    supported_values = [asset_type.value for asset_type in SUPPORTED_CLASS_TWR_TYPES]
    transaction_types_result = await db.execute(
        select(Transaction.asset_type)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_type.in_(SUPPORTED_CLASS_TWR_TYPES),
        )
        .distinct()
    )
    transaction_types = {
        getattr(value, "value", str(value)).upper()
        for value in transaction_types_result.scalars().all()
    }
    if not transaction_types:
        return False

    snapshot_result = await db.execute(
        select(
            PortfolioClassSnapshot.asset_type,
            func.max(PortfolioClassSnapshot.snapshot_date),
        )
        .where(
            PortfolioClassSnapshot.portfolio_id == portfolio_id,
            PortfolioClassSnapshot.asset_type.in_(supported_values),
        )
        .group_by(PortfolioClassSnapshot.asset_type)
    )
    latest_by_type = {row.asset_type: row[1] for row in snapshot_result.all()}
    return any(
        latest_by_type.get(asset_type) is None
        or latest_by_type[asset_type] < date.today()
        for asset_type in transaction_types
    )


async def maintain_twr_snapshots_for_active_portfolios(
    db: AsyncSession,
) -> dict[str, int]:
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
    class_snapshots = 0

    for portfolio_id in portfolio_ids:
        try:
            rebuild_consolidated = await _portfolio_needs_twr_rebuild(db, portfolio_id)
            rebuild_classes = await _portfolio_needs_class_twr_rebuild(db, portfolio_id)
            if not rebuild_consolidated and not rebuild_classes:
                skipped += 1
                continue
            if rebuild_consolidated:
                snapshots += await backfill_snapshots_with_returns(db, portfolio_id)
            if rebuild_classes:
                class_snapshots += await rebuild_class_snapshots(db, portfolio_id)
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
        "class_snapshots": class_snapshots,
    }
