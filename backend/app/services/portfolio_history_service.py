"""Historico mensal canonico para o grafico de evolucao patrimonial.

O historico consolidado usa exclusivamente PortfolioSnapshot. O ultimo snapshot de
cada mes representa o fechamento mensal. ``months <= 0`` significa todo o periodo.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_snapshot import PortfolioSnapshot


async def get_canonical_monthly_evolution(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 12,
) -> list[dict]:
    filters = [PortfolioSnapshot.portfolio_id == portfolio_id]
    if months > 0:
        filters.append(
            PortfolioSnapshot.snapshot_date >= date.today() - timedelta(days=months * 31)
        )

    monthly_last_snapshot = (
        select(
            func.date_trunc("month", PortfolioSnapshot.snapshot_date).label("month"),
            func.max(PortfolioSnapshot.snapshot_date).label("last_date"),
        )
        .where(*filters)
        .group_by(text("1"))
        .subquery()
    )

    result = await db.execute(
        select(PortfolioSnapshot)
        .join(
            monthly_last_snapshot,
            PortfolioSnapshot.snapshot_date == monthly_last_snapshot.c.last_date,
        )
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )

    return [monthly_snapshot_payload(snapshot) for snapshot in result.scalars().all()]


def monthly_snapshot_payload(snapshot: PortfolioSnapshot) -> dict:
    market_value = float(snapshot.market_value)
    cost_basis = float(snapshot.cost_basis)
    capital_result = market_value - cost_basis
    return {
        "date": snapshot.snapshot_date.isoformat(),
        "period": snapshot.snapshot_date.strftime("%Y-%m"),
        "value": market_value,
        "invested": cost_basis,
        "capital_result": round(capital_result, 2),
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": float(snapshot.unrealized_pnl),
        "realized_pnl": float(snapshot.realized_pnl),
        "total_pnl": float(snapshot.total_pnl),
        "return_pct": float(snapshot.return_pct),
        "daily_return_pct": float(snapshot.daily_return_pct),
        "accumulated_return_pct": float(snapshot.accumulated_return_pct),
        "has_partial_prices": bool(snapshot.has_partial_prices),
        "return_is_estimated": bool(snapshot.return_is_estimated),
        "history_source": "portfolio_snapshot",
    }
