"""Composição dos KPIs exibidos na página Rentabilidade.

Os valores monetários atuais vêm da mesma fonte canônica usada por Resumo e
Patrimônio. Os percentuais históricos vêm exclusivamente dos snapshots TWR.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.portfolio_snapshot_read_service import get_enriched_daily_evolution
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.realized_pnl_service import get_realized_pnl
from app.services.twr_service import compound_return_pcts


def _parse_date(point: dict) -> date | None:
    try:
        return date.fromisoformat(str(point["date"])[:10])
    except (KeyError, TypeError, ValueError):
        return None


def _period_twr(points: list[dict], start: date | None = None) -> float:
    returns: list[float] = []
    for point in points:
        point_date = _parse_date(point)
        if point_date is None or (start is not None and point_date < start):
            continue
        returns.append(float(point.get("daily_return_pct") or 0))
    return float(compound_return_pcts(returns))


async def get_rentabilidade_kpis(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna resultado canônico e rentabilidade TWR por período."""
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)
    realized_pnl = await get_realized_pnl(db, portfolio_id)

    today = date.today()
    points = await get_enriched_daily_evolution(db, portfolio_id, days=36500)
    latest = points[-1] if points else None

    month_start = today.replace(day=1)
    twelve_month_start = today - timedelta(days=365)

    return_today = float(latest.get("daily_return_pct") or 0) if latest else 0.0
    return_month = _period_twr(points, month_start)
    return_12m = _period_twr(points, twelve_month_start)
    return_since_start = (
        float(latest.get("accumulated_return_pct") or 0)
        if latest
        else 0.0
    )

    return {
        "patrimonio_atual": summary["total_patrimonio"],
        "custo_total": summary["total_investido"],
        "total_aportado": summary["total_investido"],
        "ganho_nao_realizado": summary["ganho_nao_realizado"],
        "ganho_realizado": realized_pnl,
        "total_pnl": summary["lucro_total"],
        "retorno_total_pct": return_since_start,
        "retorno_dia_pct": return_today,
        "retorno_mes_pct": return_month,
        "retorno_12m_pct": return_12m,
        "retorno_desde_inicio_pct": return_since_start,
        "proventos_total": summary["total_proventos"],
        "proventos_12m": summary["dividendos_recebidos_12m"],
        "snapshot_date": latest.get("date") if latest else None,
        "return_is_estimated": bool(latest.get("return_is_estimated", True)) if latest else True,
        "has_partial_prices": bool(latest.get("has_partial_prices", False)) if latest else False,
    }
