"""Contrato canônico da seção de rentabilidade por classe.

O valuation atual vem das posições canônicas. A rentabilidade oficial vem
exclusivamente do último ``PortfolioClassSnapshot`` materializado. Quando a
classe não possui série diária disponível, patrimônio e resultado corrente
continuam visíveis, mas nenhum retorno simples é promovido a TWR.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.services.canonical_positions_service import get_canonical_portfolio_positions
from app.services.portfolio_class_snapshot_read_service import get_class_twr_availability


_DEDICATED_CLASS_SEMANTICS: dict[str, dict[str, object]] = {
    "TESOURO_DIRETO": {
        "valuation_method": "treasury_mark_to_market",
        "valuation_label": "Marcação a mercado do Tesouro",
        "result_label": "Resultado pela marcação a mercado",
        "current_metrics_available": True,
        "dedicated_history_required": True,
        "performance_reason": (
            "O patrimônio e o resultado atuais usam a marcação a mercado do Tesouro. "
            "O TWR da classe permanece indisponível até existir uma cadeia diária "
            "segregada do motor histórico do Tesouro."
        ),
    },
    "RENDA_FIXA": {
        "valuation_method": "fixed_income_accrual",
        "valuation_label": "Atualização por indexador da aplicação",
        "result_label": "Rendimento acumulado da aplicação",
        "current_metrics_available": True,
        "dedicated_history_required": True,
        "performance_reason": (
            "O patrimônio e o rendimento atuais usam o accrual do indexador. "
            "O TWR da classe permanece indisponível até existir uma cadeia diária "
            "segregada, com fluxos e qualidade do histórico de taxas."
        ),
    },
}


def class_metric_semantics(asset_type: str) -> dict[str, object]:
    normalized = str(asset_type or "").upper()
    dedicated = _DEDICATED_CLASS_SEMANTICS.get(normalized)
    if dedicated is not None:
        return dict(dedicated)
    return {
        "valuation_method": "intraday_market_valuation",
        "valuation_label": "Valuation de mercado intradiário",
        "result_label": "Resultado patrimonial atual",
        "current_metrics_available": True,
        "dedicated_history_required": False,
        "performance_reason": None,
    }


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
        semantics = class_metric_semantics(asset_type)
        current_value = float(group.get("total_value") or 0)
        invested = float(group.get("total_invested") or 0)
        twr_available = bool(snapshot is not None and status.get("available"))
        performance_reason = status.get("reason")
        if not twr_available and semantics.get("performance_reason"):
            performance_reason = semantics["performance_reason"]

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
                "current_metrics_available": bool(semantics["current_metrics_available"]),
                "valuation_method": semantics["valuation_method"],
                "valuation_label": semantics["valuation_label"],
                "result_label": semantics["result_label"],
                "dedicated_history_required": bool(semantics["dedicated_history_required"]),
                "twr_available": twr_available,
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
                "performance_reason": performance_reason,
                "performance_source": (
                    "portfolio_class_snapshot" if snapshot else None
                ),
            }
        )

    return rows
