"""Leitura dos snapshots canônicos por classe."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetType
from app.models.fixed_income import FixedIncomeInvestment
from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.transaction import Transaction
from app.services.portfolio_class_snapshot_service import class_twr_availability
from app.services.portfolio_evolution_period_service import monthly_window_start
from app.services.twr_service import compound_return_pcts


def class_snapshot_payload(snapshot: PortfolioClassSnapshot) -> dict:
    return {
        "asset_type": snapshot.asset_type,
        "date": snapshot.snapshot_date.isoformat(),
        "market_value": float(snapshot.market_value),
        "cost_basis": float(snapshot.cost_basis),
        "realized_pnl": float(snapshot.realized_pnl),
        "unrealized_pnl": float(snapshot.unrealized_pnl),
        "net_external_flow": float(snapshot.net_external_flow),
        "dividends_day": float(snapshot.dividends_day),
        "dividends_accumulated": float(snapshot.dividends_accumulated),
        "daily_return_pct": float(snapshot.daily_return_pct),
        "accumulated_return_pct": float(snapshot.accumulated_return_pct),
        "has_partial_prices": bool(snapshot.has_partial_prices),
        "return_is_estimated": bool(snapshot.return_is_estimated),
        "valuation_status": snapshot.valuation_status,
        "history_source": "portfolio_class_snapshot",
    }


async def get_class_twr_availability(db: AsyncSession, portfolio_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    types: set[AssetType] = set()
    for value in result.scalars().all():
        raw = getattr(value, "value", value)
        try:
            types.add(AssetType(str(raw).upper()))
        except (TypeError, ValueError):
            continue

    fixed_income_result = await db.execute(
        select(func.count(FixedIncomeInvestment.id)).where(
            FixedIncomeInvestment.portfolio_id == portfolio_id,
            FixedIncomeInvestment.is_active.is_(True),
        )
    )
    if int(fixed_income_result.scalar_one() or 0) > 0:
        types.add(AssetType.RENDA_FIXA)

    latest_result = await db.execute(
        select(
            PortfolioClassSnapshot.asset_type,
            func.max(PortfolioClassSnapshot.snapshot_date),
        )
        .where(PortfolioClassSnapshot.portfolio_id == portfolio_id)
        .group_by(PortfolioClassSnapshot.asset_type)
    )
    latest_by_type = {row.asset_type: row[1] for row in latest_result.all()}

    rows = class_twr_availability(types)
    for row in rows:
        latest = latest_by_type.get(row["asset_type"])
        row["engine_supported"] = row["available"]
        row["data_available"] = latest is not None
        row["latest_snapshot_date"] = latest.isoformat() if latest is not None else None
        row["available"] = bool(row["engine_supported"] and row["data_available"])
        if row["engine_supported"] and not row["data_available"]:
            row["status"] = "awaiting_backfill"
            row["reason"] = "O motor é suportado, mas o histórico por classe ainda não foi materializado."
    return rows


async def get_daily_class_evolution(
    db: AsyncSession,
    portfolio_id: int,
    asset_type: str,
    days: int = 365,
) -> list[dict]:
    query = select(PortfolioClassSnapshot).where(
        PortfolioClassSnapshot.portfolio_id == portfolio_id,
        PortfolioClassSnapshot.asset_type == asset_type.upper(),
    )
    if days > 0:
        query = query.where(
            PortfolioClassSnapshot.snapshot_date >= date.today() - timedelta(days=days)
        )
    result = await db.execute(query.order_by(PortfolioClassSnapshot.snapshot_date.asc()))
    return [class_snapshot_payload(row) for row in result.scalars().all()]


async def get_monthly_class_evolution(
    db: AsyncSession,
    portfolio_id: int,
    asset_type: str,
    months: int = 24,
) -> list[dict]:
    query = select(PortfolioClassSnapshot).where(
        PortfolioClassSnapshot.portfolio_id == portfolio_id,
        PortfolioClassSnapshot.asset_type == asset_type.upper(),
    )
    start_date = monthly_window_start(months)
    if start_date is not None:
        query = query.where(PortfolioClassSnapshot.snapshot_date >= start_date)
    result = await db.execute(query.order_by(PortfolioClassSnapshot.snapshot_date.asc()))
    rows = list(result.scalars().all())
    grouped: dict[str, list[PortfolioClassSnapshot]] = defaultdict(list)
    for row in rows:
        grouped[row.snapshot_date.strftime("%Y-%m")].append(row)

    payloads: list[dict] = []
    for period, period_rows in grouped.items():
        last = period_rows[-1]
        payload = class_snapshot_payload(last)
        payload["period"] = period
        payload["monthly_return_pct"] = float(
            compound_return_pcts(Decimal(str(row.daily_return_pct)) for row in period_rows)
        )
        payloads.append(payload)
    return payloads
