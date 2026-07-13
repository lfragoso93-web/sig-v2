"""Composicao dos KPIs exibidos na pagina Rentabilidade.

Os valores atuais da carteira vem da mesma fonte canonica usada por Resumo e
Patrimonio. O ganho realizado usa o servico canonico compartilhado. Os retornos
por periodo ainda sao legados e serao substituidos pelo TWR dos snapshots.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.portfolio_snapshot_service import get_daily_evolution
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.realized_pnl_service import calculate_realized_pnl, get_realized_pnl


def _period_return(
    points: list[dict],
    target_date: date,
    current_market_value: float,
    current_total_pnl: float,
) -> float:
    """Calcula retorno legado usando o ultimo ponto anterior a referencia."""
    if not points:
        return 0.0

    parsed: list[tuple[date, dict]] = []
    for point in points:
        try:
            parsed.append((date.fromisoformat(str(point["date"])[:10]), point))
        except (KeyError, TypeError, ValueError):
            continue

    if not parsed:
        return 0.0

    parsed.sort(key=lambda item: item[0])
    candidates = [item for item in parsed if item[0] <= target_date]
    baseline = candidates[-1][1] if candidates else parsed[0][1]

    baseline_market = float(
        baseline.get("market_value")
        or baseline.get("invested_total")
        or baseline.get("cost_basis")
        or 0
    )
    if baseline_market <= 0:
        return 0.0

    baseline_pnl = float(baseline.get("total_pnl") or 0)
    return round((current_total_pnl - baseline_pnl) / baseline_market * 100, 4)


async def get_rentabilidade_kpis(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna KPIs atuais canonicos combinados com metricas historicas legadas."""
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)
    realized_pnl = await get_realized_pnl(db, portfolio_id)

    today = date.today()
    month_reference = today.replace(day=1) - timedelta(days=1)
    twelve_month_reference = today - timedelta(days=365)

    month_points = await get_daily_evolution(db, portfolio_id, days=45)
    year_points = await get_daily_evolution(db, portfolio_id, days=370)

    current_market_value = float(summary["total_patrimonio"])
    current_total_pnl = float(summary["lucro_total"])

    return {
        "patrimonio_atual": summary["total_patrimonio"],
        "custo_total": summary["total_investido"],
        "total_aportado": summary["total_investido"],
        "ganho_nao_realizado": summary["ganho_nao_realizado"],
        "total_pnl": summary["lucro_total"],
        "retorno_total_pct": summary["rentabilidade_total"],
        "retorno_desde_inicio_pct": summary["rentabilidade_total"],
        "proventos_total": summary["total_proventos"],
        "proventos_12m": summary["dividendos_recebidos_12m"],
        "ganho_realizado": realized_pnl,
        "retorno_dia_pct": 0.0,
        "retorno_mes_pct": _period_return(
            month_points,
            month_reference,
            current_market_value,
            current_total_pnl,
        ),
        "retorno_12m_pct": _period_return(
            year_points,
            twelve_month_reference,
            current_market_value,
            current_total_pnl,
        ),
        "snapshot_date": today.isoformat(),
    }
