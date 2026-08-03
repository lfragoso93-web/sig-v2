"""Inspeção read-only do estado persistido de proventos."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
)


async def inspect_dividends_seed_groupings(
    db: AsyncSession,
) -> tuple[dict, ...]:
    """Agrupa o estado final canônico sem alterar a sessão."""

    dimensions = (
        Asset.asset_type,
        AssetDividend.dividend_type,
        AssetDividend.source,
        func.extract("year", AssetDividend.ex_date),
        Asset.ticker,
    )
    global_rows = (
        await db.execute(
            select(*dimensions, func.count(AssetDividend.id))
            .select_from(AssetDividend)
            .join(Asset, Asset.id == AssetDividend.asset_id)
            .group_by(*dimensions)
            .order_by(*dimensions)
        )
    ).all()
    grouped: dict[tuple[str, str, str, int, str], dict] = {}
    for asset_type, event_type, source, year, ticker, count in global_rows:
        key = (
            str(asset_type),
            str(getattr(event_type, "value", event_type)),
            str(source),
            int(year),
            str(ticker).strip().upper(),
        )
        grouped[key] = {
            "asset_class": key[0],
            "event_type": key[1],
            "source": key[2],
            "year": key[3],
            "ticker": key[4],
            "global_events": int(count),
        }
    return tuple(grouped[key] for key in sorted(grouped))


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
        asset_dividends=await _count_rows(db, AssetDividend),
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
    coverage = DividendsSeedCoverage(
        first_ex_date=(
            coverage_row.first_ex_date.isoformat()
            if coverage_row.first_ex_date
            else None
        ),
        last_ex_date=(
            coverage_row.last_ex_date.isoformat() if coverage_row.last_ex_date else None
        ),
        assets_with_events=int(coverage_row.assets_with_events or 0),
    )

    duplicate_global_events = await _count_duplicate_rows(
        db,
        select(
            AssetDividend.asset_id,
            AssetDividend.ex_date,
            AssetDividend.dividend_type,
            func.coalesce(AssetDividend.payment_date, AssetDividend.ex_date),
            func.count(AssetDividend.id).label("rows"),
        )
        .group_by(
            AssetDividend.asset_id,
            AssetDividend.ex_date,
            AssetDividend.dividend_type,
            func.coalesce(AssetDividend.payment_date, AssetDividend.ex_date),
        )
        .having(func.count(AssetDividend.id) > 1),
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
    missing_ex_dates = int(
        await db.scalar(
            select(func.count(AssetDividend.id)).where(AssetDividend.ex_date.is_(None))
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
    integrity = DividendsSeedIntegrity(
        duplicate_global_events=duplicate_global_events,
        orphan_asset_dividends=orphan_asset_dividends,
        missing_ex_dates=missing_ex_dates,
        negative_monetary_values=negative_global_values,
    )
    return counts, coverage, integrity
