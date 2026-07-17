"""Composição canônica dos KPIs exibidos na página Rentabilidade.

Valores monetários atuais vêm de ``summary.v2``. Percentuais de performance vêm
exclusivamente dos snapshots TWR fechados. Ausência de snapshots resulta em
``None``; nunca em retorno simples ou zero artificial.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.rentabilidade import RentabilidadeKpisResponse
from app.services.portfolio_snapshot_read_service import get_enriched_daily_evolution
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.twr_service import compound_return_pcts


def _parse_date(point: dict) -> date | None:
    try:
        return date.fromisoformat(str(point["date"])[:10])
    except (KeyError, TypeError, ValueError):
        return None


def _period_twr(points: list[dict], start: date | None = None) -> float | None:
    returns: list[float] = []
    for point in points:
        point_date = _parse_date(point)
        if point_date is None or (start is not None and point_date < start):
            continue
        returns.append(float(point.get("daily_return_pct") or 0))
    if not returns:
        return None
    return float(compound_return_pcts(returns))


async def get_rentabilidade_kpis(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna o contrato ``rentabilidade.v2`` validado em runtime."""
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)

    today = date.today()
    points = await get_enriched_daily_evolution(db, portfolio_id, days=0)
    latest = points[-1] if points else None

    month_start = today.replace(day=1)
    twelve_month_start = today - timedelta(days=365)

    payload = {
        "contract_version": "rentabilidade.v2",
        "patrimonio_atual": summary["total_patrimonio"],
        "custo_posicoes_abertas": summary["total_investido"],
        "resultado_nao_realizado": summary["ganho_nao_realizado"],
        "resultado_realizado": summary["ganho_realizado"],
        "resultado_total": summary["lucro_total"],
        "proventos_total": summary["total_proventos"],
        "proventos_12m": summary["dividendos_recebidos_12m"],
        "twr_dia_pct": float(latest.get("daily_return_pct") or 0) if latest else None,
        "twr_mes_pct": _period_twr(points, month_start),
        "twr_12m_pct": _period_twr(points, twelve_month_start),
        "twr_desde_inicio_pct": (
            float(latest.get("accumulated_return_pct") or 0) if latest else None
        ),
        "valuation_updated_at": summary.get("valuation_updated_at"),
        "performance_as_of": latest.get("date") if latest else None,
        "proventos_as_of": summary.get("proventos_as_of"),
        "return_is_estimated": (
            bool(latest.get("return_is_estimated", True)) if latest else True
        ),
        "has_partial_prices": (
            bool(latest.get("has_partial_prices", False)) if latest else False
        ),
        "price_coverage_pct": float(summary.get("price_coverage_pct", 100.0)),
        "performance_source": "portfolio_snapshot_twr" if latest else "unavailable",
    }
    return RentabilidadeKpisResponse.model_validate(payload).model_dump()
