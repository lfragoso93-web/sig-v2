"""Inspeção read-only do estado persistido de proventos."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend
from app.models.dividends_sync_job import DividendsSyncJob
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
)


async def _count_rows(db: AsyncSession, model: type) -> int:
    return int(await db.scalar(select(func.count()).select_from(model)) or 0)


async def _count_duplicate_rows(db: AsyncSession, statement) -> int:
    result = await db.execute(statement)
    return sum(max(int(row.rows) - 1, 0) for row in result.all())


async def inspect_dividends_seed_state(
    db: AsyncSession,
) -> tuple[DividendsSeedCounts, DividendsSeedCoverage, DividendsSeedIntegrity]:
    """Lê baseline, cobertura e integridade sem alterar a sessão."""

    counts = DividendsSeedCounts(
        assets=await _count_rows(db, Asset),
        transactions=await _count_rows(db, Transaction),
        portfolios=await _count_rows(db, Portfolio),
        asset_dividends=await _count_rows(db, AssetDividend),
        dividends=await _count_rows(db, Dividend),
        sync_jobs=await _count_rows(db, DividendsSyncJob),
    )

    coverage_result = await db.execute(
        select(
            func.min(AssetDividend.ex_date).label("first_ex_date"),
            func.max(AssetDividend.ex_date).label("last_ex_date"),
            func.count(func.distinct(AssetDividend.asset_id)).label(
                "assets_with_events"
            ),
        )
    )
    coverage_row = coverage_result.one()
    portfolios_with_dividends = int(
        await db.scalar(
            select(func.count(func.distinct(Dividend.portfolio_id)))
        )
        or 0
    )
    coverage = DividendsSeedCoverage(
        first_ex_date=(
            coverage_row.first_ex_date.isoformat()
            if coverage_row.first_ex_date
            else None
        ),
        last_ex_date=(
            coverage_row.last_ex_date.isoformat()
            if coverage_row.last_ex_date
            else None
        ),
        assets_with_events=int(coverage_row.assets_with_events or 0),
        portfolios_with_dividends=portfolios_with_dividends,
    )

    duplicate_global_events = await _count_duplicate_rows(
        db,
        select(
            AssetDividend.asset_id,
            AssetDividend.ex_date,
            AssetDividend.dividend_type,
            func.count(AssetDividend.id).label("rows"),
        )
        .group_by(
            AssetDividend.asset_id,
            AssetDividend.ex_date,
            AssetDividend.dividend_type,
        )
        .having(func.count(AssetDividend.id) > 1),
    )
    duplicate_materializations = await _count_duplicate_rows(
        db,
        select(
            Dividend.portfolio_id,
            Dividend.asset_dividend_id,
            func.count(Dividend.id).label("rows"),
        )
        .where(Dividend.asset_dividend_id.is_not(None))
        .group_by(Dividend.portfolio_id, Dividend.asset_dividend_id)
        .having(func.count(Dividend.id) > 1),
    )

    orphan_asset_dividends = int(
        await db.scalar(
            select(func.count(AssetDividend.id))
            .select_from(AssetDividend)
            .outerjoin(Asset, Asset.id == AssetDividend.asset_id)
            .where(Asset.id.is_(None))
        )
        or 0
    )
    orphan_dividend_events = int(
        await db.scalar(
            select(func.count(Dividend.id))
            .select_from(Dividend)
            .outerjoin(
                AssetDividend,
                AssetDividend.id == Dividend.asset_dividend_id,
            )
            .where(
                Dividend.asset_dividend_id.is_not(None),
                AssetDividend.id.is_(None),
            )
        )
        or 0
    )
    orphan_dividend_portfolios = int(
        await db.scalar(
            select(func.count(Dividend.id))
            .select_from(Dividend)
            .outerjoin(Portfolio, Portfolio.id == Dividend.portfolio_id)
            .where(Portfolio.id.is_(None))
        )
        or 0
    )
    missing_ex_dates = int(
        await db.scalar(
            select(func.count(AssetDividend.id)).where(
                AssetDividend.ex_date.is_(None)
            )
        )
        or 0
    )
    negative_global_values = int(
        await db.scalar(
            select(func.count(AssetDividend.id)).where(
                or_(
                    AssetDividend.value_per_unit < 0,
                    AssetDividend.gross_value_per_unit < 0,
                )
            )
        )
        or 0
    )
    negative_materialized_values = int(
        await db.scalar(
            select(func.count(Dividend.id)).where(
                or_(
                    Dividend.value_per_unit < 0,
                    Dividend.total_value < 0,
                    Dividend.net_value < 0,
                    Dividend.total_received < 0,
                )
            )
        )
        or 0
    )

    integrity = DividendsSeedIntegrity(
        duplicate_global_events=duplicate_global_events,
        duplicate_materializations=duplicate_materializations,
        orphan_asset_dividends=orphan_asset_dividends,
        orphan_dividend_events=orphan_dividend_events,
        orphan_dividend_portfolios=orphan_dividend_portfolios,
        missing_ex_dates=missing_ex_dates,
        negative_monetary_values=(
            negative_global_values + negative_materialized_values
        ),
    )
    return counts, coverage, integrity
