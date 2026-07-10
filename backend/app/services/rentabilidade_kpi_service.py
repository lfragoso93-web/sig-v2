"""Composicao dos KPIs exibidos na pagina Rentabilidade.

Os valores atuais da carteira devem vir da mesma fonte canonica usada por Resumo
e Patrimonio. Metricas historicas de periodo e ganho realizado continuam sendo
calculadas pelo servico especializado de rentabilidade.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.rentabilidade_service import get_kpis as get_legacy_rentabilidade_kpis


async def get_rentabilidade_kpis(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna KPIs atuais canonicos combinados com metricas historicas."""
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)
    historical = await get_legacy_rentabilidade_kpis(db, portfolio_id)

    return {
        # Valores atuais: mesma fonte de Resumo e Patrimonio.
        "patrimonio_atual": summary["total_patrimonio"],
        "custo_total": summary["total_investido"],
        "total_aportado": summary["total_investido"],
        "ganho_nao_realizado": summary["ganho_capital"],
        "total_pnl": summary["lucro_total"],
        "retorno_total_pct": summary["rentabilidade_total"],
        "retorno_desde_inicio_pct": summary["rentabilidade_total"],
        "proventos_total": summary["total_proventos"],
        "proventos_12m": summary["dividendos_recebidos_12m"],
        # Metricas especializadas mantidas no modulo de rentabilidade.
        "ganho_realizado": historical.get("ganho_realizado", 0.0),
        "retorno_dia_pct": historical.get("retorno_dia_pct", 0.0),
        "retorno_mes_pct": historical.get("retorno_mes_pct", 0.0),
        "retorno_12m_pct": historical.get("retorno_12m_pct", 0.0),
        "snapshot_date": historical.get("snapshot_date"),
    }
