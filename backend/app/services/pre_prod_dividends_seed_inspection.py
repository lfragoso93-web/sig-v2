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
from app.services.dividend_entitlement_service import calculate_net_quantity
from app.services.dividend_type_service import (
    CASH_DIVIDEND_TYPES,
    normalize_dividend_type,
)
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
    materialized_rows = (
        await db.execute(
            select(*dimensions, func.count(Dividend.id))
            .select_from(Dividend)
            .join(
                AssetDividend,
                AssetDividend.id == Dividend.asset_dividend_id,
            )
            .join(Asset, Asset.id == AssetDividend.asset_id)
            .group_by(*dimensions)
            .order_by(*dimensions)
        )
    ).all()

    grouped: dict[tuple[str, str, str, int, str], dict] = {}
    for rows, field in (
        (global_rows, "global_events"),
        (materialized_rows, "materialized_rights"),
    ):
        for asset_type, event_type, source, year, ticker, count in rows:
            key = (
                str(asset_type),
                str(getattr(event_type, "value", event_type)),
                str(source),
                int(year),
                str(ticker).strip().upper(),
            )
            item = grouped.setdefault(
                key,
                {
                    "asset_class": key[0],
                    "event_type": key[1],
                    "source": key[2],
                    "year": key[3],
                    "ticker": key[4],
                    "global_events": 0,
                    "materialized_rights": 0,
                },
            )
            item[field] = int(count)
    return tuple(grouped[key] for key in sorted(grouped))


async def _count_rows(db: AsyncSession, model: type) -> int:
    return int(await db.scalar(select(func.count()).select_from(model)) or 0)


async def _count_duplicate_rows(db: AsyncSession, statement) -> int:
    result = await db.execute(statement)
    return sum(max(int(row.rows) - 1, 0) for row in result.all())


async def _inspect_materialization_coverage(
    db: AsyncSession,
) -> tuple[int, int, int, int]:
    event_rows = (
        await db.execute(
            select(
                AssetDividend.id,
                AssetDividend.record_date,
                AssetDividend.ex_date,
                AssetDividend.dividend_type,
                Asset.ticker,
            )
            .join(Asset, Asset.id == AssetDividend.asset_id)
            .order_by(AssetDividend.id)
        )
    ).all()
    transaction_rows = (
        await db.execute(
            select(
                Transaction.portfolio_id,
                Transaction.ticker,
                Transaction.date,
                Transaction.operation,
                Transaction.quantity,
            )
        )
    ).all()
    right_rows = (
        await db.execute(
            select(Dividend.portfolio_id, Dividend.asset_dividend_id).where(
                Dividend.asset_dividend_id.is_not(None)
            )
        )
    ).all()

    transactions: dict[tuple[int, str], list[tuple]] = {}
    portfolio_ids: set[int] = set()
    for portfolio_id, ticker, tx_date, operation, quantity in transaction_rows:
        normalized_ticker = str(ticker).strip().upper()
        portfolio_ids.add(portfolio_id)
        transactions.setdefault((portfolio_id, normalized_ticker), []).append(
            (tx_date, operation, quantity)
        )

    eligible: set[tuple[int, int]] = set()
    for event_id, record_date, ex_date, event_type, ticker in event_rows:
        if normalize_dividend_type(event_type) not in CASH_DIVIDEND_TYPES:
            continue
        entitlement_date = record_date or ex_date
        normalized_ticker = str(ticker).strip().upper()
        for portfolio_id in portfolio_ids:
            quantity = calculate_net_quantity(
                transactions.get((portfolio_id, normalized_ticker), []),
                entitlement_date,
            )
            if quantity > 0:
                eligible.add((portfolio_id, event_id))

    materialized = {
        (portfolio_id, event_id)
        for portfolio_id, event_id in right_rows
        if event_id is not None
    }
    materialized_eligible = eligible & materialized
    return (
        len(eligible),
        len(materialized_eligible),
        len(eligible - materialized),
        len(materialized - eligible),
    )


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
        await db.scalar(select(func.count(func.distinct(Dividend.portfolio_id)))) or 0
    )
    (
        eligible_materializations,
        materialized_eligible_rights,
        missing_materializations,
        materializations_without_entitlement,
    ) = await _inspect_materialization_coverage(db)
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
        portfolios_with_dividends=portfolios_with_dividends,
        eligible_materializations=eligible_materializations,
        materialized_eligible_rights=materialized_eligible_rights,
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
        duplicate_materializations=duplicate_materializations,
        orphan_asset_dividends=orphan_asset_dividends,
        orphan_dividend_events=orphan_dividend_events,
        orphan_dividend_portfolios=orphan_dividend_portfolios,
        missing_ex_dates=missing_ex_dates,
        negative_monetary_values=negative_global_values,
        missing_materializations=missing_materializations,
        materializations_without_entitlement=(materializations_without_entitlement),
    )
    return counts, coverage, integrity
