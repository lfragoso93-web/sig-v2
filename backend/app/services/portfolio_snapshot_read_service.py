"""Leitura canônica dos snapshots patrimoniais enriquecidos com TWR."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.twr_service import compound_return_pcts


def snapshot_to_enriched_payload(
    snapshot: PortfolioSnapshot,
    *,
    include_monthly_aliases: bool = False,
) -> dict:
    """Serializa patrimônio fechado, custo atual, fluxos e performance."""
    payload = {
        "date": snapshot.snapshot_date.strftime("%Y-%m-%d"),
        "market_value": float(snapshot.market_value),
        "cost_basis": float(snapshot.cost_basis),
        "invested_total": float(snapshot.invested_total),
        "net_external_flow": float(snapshot.net_external_flow),
        "unrealized_pnl": float(snapshot.unrealized_pnl),
        "realized_pnl": float(snapshot.realized_pnl),
        "total_pnl": float(snapshot.total_pnl),
        "return_pct": float(snapshot.return_pct),
        "dividends_day": float(snapshot.dividends_day),
        "dividends_accumulated": float(snapshot.dividends_accumulated),
        "daily_return_pct": float(snapshot.daily_return_pct),
        "accumulated_return_pct": float(snapshot.accumulated_return_pct),
        "has_partial_prices": bool(snapshot.has_partial_prices),
        "return_is_estimated": bool(snapshot.return_is_estimated),
        "history_source": "portfolio_snapshot",
    }
    if include_monthly_aliases:
        payload.update(
            {
                "value": payload["market_value"],
                # Na página Patrimônio, "investido" significa o custo atual das
                # posições abertas, igual ao contrato summary.v2.
                "invested": payload["cost_basis"],
                "period": snapshot.snapshot_date.strftime("%Y-%m"),
                "monthly_return_pct": payload["daily_return_pct"],
            }
        )
    return payload


async def get_enriched_daily_evolution(
    db: AsyncSession,
    portfolio_id: int,
    days: int = 365,
) -> list[dict]:
    query = select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id)
    if days > 0:
        query = query.where(PortfolioSnapshot.snapshot_date >= date.today() - timedelta(days=days))
    result = await db.execute(query.order_by(PortfolioSnapshot.snapshot_date.asc()))
    return [snapshot_to_enriched_payload(row) for row in result.scalars().all()]


async def get_enriched_monthly_evolution(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 24,
) -> list[dict]:
    """Retorna o último snapshot de cada mês com retorno mensal composto."""
    query = select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id)
    if months > 0:
        query = query.where(PortfolioSnapshot.snapshot_date >= date.today() - timedelta(days=months * 31))
    rows_result = await db.execute(query.order_by(PortfolioSnapshot.snapshot_date.asc()))
    rows = list(rows_result.scalars().all())
    if not rows:
        return []

    grouped: dict[str, list[PortfolioSnapshot]] = {}
    for row in rows:
        grouped.setdefault(row.snapshot_date.strftime("%Y-%m"), []).append(row)

    payloads: list[dict] = []
    for month_rows in grouped.values():
        monthly_return = compound_return_pcts(
            Decimal(str(row.daily_return_pct)) for row in month_rows
        )
        payload = snapshot_to_enriched_payload(month_rows[-1], include_monthly_aliases=True)
        payload["monthly_return_pct"] = float(monthly_return)
        payloads.append(payload)
    return payloads
