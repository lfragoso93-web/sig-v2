"""Contrato canônico da seção de rentabilidade por classe.

O valuation atual vem das posições intradiárias. A rentabilidade oficial vem
exclusivamente do último ``PortfolioClassSnapshot`` materializado. Quando a
classe não possui série disponível, nenhum retorno simples é promovido a TWR.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.services.canonical_positions_service import get_canonical_portfolio_positions
from app.services.portfolio_class_snapshot_read_service import get_class_twr_availability


async def _latest_snapshots_by_class(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, PortfolioClassSnapshot]:
    result = await db.execute(
        select(PortfolioClassSnapshot)
        .where(PortfolioClassSnapshot.portfolio_id == portfolio_id)
        .order_by(
            PortfolioClassSnapshot.asset_type.asc(),
            PortfolioClassSnapshot.snapshot_date.desc(),
        )
    )
    latest: dict[str, PortfolioClassSnapshot] = {}
    for snapshot in result.scalars().all():
        latest.setdefault(str(snapshot.asset_type).upper(), snapshot)
    return latest


def _group_asset_type(group: dict) -> str:
    direct = group.get("asset_type") or group.get("type")
    if direct:
        return str(direct).upper()
    for position in group.get("positions", []):
        value = position.get("asset_type")
        if value:
            return str(value).upper()
    return ""


async def get_canonical_class_performance(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[dict]:
    groups = await get_canonical_portfolio_positions(db, portfolio_id, user_id)
    snapshots = await _latest_snapshots_by_class(db, portfolio_id)
    availability_rows = await get_class_twr_availability(db, portfolio_id)
    availability = {
        str(row["asset_type"]).upper(): row
        for row in availability_rows
    }

    total_portfolio_value = sum(float(group.get("total_value") or 0) for group in groups)
    rows: list[dict] = []

    for group in groups:
        asset_type = _group_asset_type(group)
        if not asset_type:
            continue

        snapshot = snapshots.get(asset_type)
        status = availability.get(asset_type, {})
        current_value = float(group.get("total_value") or 0)
        invested = float(group.get("total_invested") or 0)

        rows.append(
            {
                "asset_type": asset_type,
                "current_value": round(current_value, 2),
                "cost_basis": round(invested, 2),
                "capital_result_value": group.get("capital_result_value"),
                "capital_result_pct": group.get("capital_result_pct"),
                "received_dividends": group.get("received_dividends", 0.0),
                "total_result_value": group.get("total_result_value"),
                "total_result_pct": group.get("total_result_pct"),
                "allocation_pct": round(
                    current_value / total_portfolio_value * 100,
                    4,
                ) if total_portfolio_value > 0 else 0.0,
                "asset_count": int(group.get("count") or len(group.get("positions", []))),
                "twr_available": bool(snapshot is not None and status.get("available")),
                "daily_twr_pct": float(snapshot.daily_return_pct) if snapshot else None,
                "accumulated_twr_pct": (
                    float(snapshot.accumulated_return_pct) if snapshot else None
                ),
                "performance_as_of": (
                    snapshot.snapshot_date.isoformat() if snapshot else None
                ),
                "has_partial_prices": bool(snapshot.has_partial_prices) if snapshot else None,
                "return_is_estimated": bool(snapshot.return_is_estimated) if snapshot else None,
                "performance_status": status.get("status", "not_available"),
                "performance_reason": status.get("reason"),
                "performance_source": (
                    "portfolio_class_snapshot" if snapshot else None
                ),
            }
        )

    return rows
