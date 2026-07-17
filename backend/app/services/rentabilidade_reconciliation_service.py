"""Diagnóstico de reconciliação da página Rentabilidade."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rentabilidade_class_service import get_canonical_class_performance
from app.services.rentabilidade_kpi_service import get_rentabilidade_kpis
from app.services.portfolio_summary_service import get_canonical_portfolio_summary

_TOLERANCE = 0.01


def _difference(left: float, right: float) -> float:
    return round(left - right, 2)


def _matches(left: float, right: float) -> bool:
    return abs(left - right) <= _TOLERANCE


async def reconcile_rentabilidade_page(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)
    kpis = await get_rentabilidade_kpis(db, portfolio_id, user_id)
    classes = await get_canonical_class_performance(db, portfolio_id, user_id)

    monetary = {
        "patrimonio": {
            "rentabilidade": float(kpis["patrimonio_atual"]),
            "summary": float(summary["total_patrimonio"]),
        },
        "cost_basis": {
            "rentabilidade": float(kpis["custo_posicoes_abertas"]),
            "summary": float(summary["total_investido"]),
        },
        "resultado_nao_realizado": {
            "rentabilidade": float(kpis["resultado_nao_realizado"]),
            "summary": float(summary["ganho_nao_realizado"]),
        },
        "resultado_realizado": {
            "rentabilidade": float(kpis["resultado_realizado"]),
            "summary": float(summary["ganho_realizado"]),
        },
        "resultado_total": {
            "rentabilidade": float(kpis["resultado_total"]),
            "summary": float(summary["lucro_total"]),
        },
        "proventos": {
            "rentabilidade": float(kpis["proventos_total"]),
            "summary": float(summary["total_proventos"]),
        },
    }
    for values in monetary.values():
        values["difference"] = _difference(values["rentabilidade"], values["summary"])
        values["matches"] = _matches(values["rentabilidade"], values["summary"])

    class_value = round(sum(float(row.get("current_value") or 0) for row in classes), 2)
    class_cost = round(sum(float(row.get("cost_basis") or 0) for row in classes), 2)
    class_reconciliation = {
        "patrimonio": {
            "classes": class_value,
            "summary": float(summary["total_patrimonio"]),
            "difference": _difference(class_value, float(summary["total_patrimonio"])),
            "matches": _matches(class_value, float(summary["total_patrimonio"])),
        },
        "cost_basis": {
            "classes": class_cost,
            "summary": float(summary["total_investido"]),
            "difference": _difference(class_cost, float(summary["total_investido"])),
            "matches": _matches(class_cost, float(summary["total_investido"])),
        },
    }

    all_matches = all(item["matches"] for item in monetary.values()) and all(
        item["matches"] for item in class_reconciliation.values()
    )
    unsupported_twr = [
        row["asset_type"] for row in classes
        if row.get("dedicated_history_required") and not row.get("twr_available")
    ]

    return {
        "reconciliation_version": "rentabilidade.reconciliation.v1",
        "is_reconciled": all_matches,
        "tolerance": _TOLERANCE,
        "monetary": monetary,
        "classes": class_reconciliation,
        "performance_as_of": kpis.get("performance_as_of"),
        "unsupported_class_twr": unsupported_twr,
        "twr_comparability_status": (
            "partial_by_design" if unsupported_twr else "all_classes_supported"
        ),
    }
