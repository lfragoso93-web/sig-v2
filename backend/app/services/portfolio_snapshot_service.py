"""Operações destrutivas compartilhadas para snapshots de carteira.

A materialização de ``PortfolioSnapshot`` pertence exclusivamente ao writer TWR
canônico em ``portfolio_snapshot_canonical_twr_service``. Este módulo preserva
somente a invalidação por data usada antes de reconstruções canônicas.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_snapshot import PortfolioSnapshot

logger = logging.getLogger(__name__)


async def invalidate_snapshots_from(
    db: AsyncSession,
    portfolio_id: int,
    from_date: date,
    commit: bool = False,
) -> int:
    """Remove snapshots a partir de ``from_date`` antes de rebuild canônico."""
    stmt = delete(PortfolioSnapshot).where(
        PortfolioSnapshot.portfolio_id == portfolio_id,
        PortfolioSnapshot.snapshot_date >= from_date,
    )
    result = await db.execute(stmt)
    deleted = result.rowcount
    if commit:
        await db.commit()
    logger.info(
        "[snapshot] invalidate portfolio=%s from=%s — %s snapshots removidos",
        portfolio_id,
        from_date,
        deleted,
    )
    return deleted
