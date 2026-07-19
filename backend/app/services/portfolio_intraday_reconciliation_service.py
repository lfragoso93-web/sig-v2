"""Reconciliação dos consumidores do valuation intradiário canônico.

Este serviço não lê snapshots nem compara TWR. Ele confronta apenas valores
monetários publicados na mesma referência intradiária pelo Resumo, grupos de
posições e distribuição por classe.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.canonical_positions_service import get_canonical_portfolio_positions
from app.services.portfolio_reconciliation_service import (
    MONEY_TOLERANCE,
    build_reconciliation_check,
)
from app.services.portfolio_service import get_asset_distribution
from app.services.portfolio_summary_service import get_canonical_portfolio_summary


def _money_sum(items: Sequence[Mapping[str, object]], field: str) -> Decimal:
    return sum(
        (Decimal(str(item.get(field) or 0)) for item in items),
        Decimal("0"),
    )


def reconcile_intraday_consumers(
    summary: Mapping[str, object],
    position_groups: Sequence[Mapping[str, object]],
    asset_distribution: Sequence[Mapping[str, object]],
) -> dict:
    """Compara consumidores intradiários com tolerância monetária de um centavo."""
    position_market_value = _money_sum(position_groups, "total_value")
    position_cost_basis = _money_sum(position_groups, "total_invested")
    position_unrealized_pnl = _money_sum(position_groups, "capital_result_value")
    distribution_market_value = _money_sum(asset_distribution, "value")

    checks = [
        build_reconciliation_check(
            "positions.total_patrimonio",
            summary.get("total_patrimonio"),
            position_market_value,
        ),
        build_reconciliation_check(
            "positions.total_investido",
            summary.get("total_investido"),
            position_cost_basis,
        ),
        build_reconciliation_check(
            "positions.ganho_nao_realizado",
            summary.get("ganho_nao_realizado"),
            position_unrealized_pnl,
        ),
        build_reconciliation_check(
            "asset_distribution.total_patrimonio",
            summary.get("total_patrimonio"),
            distribution_market_value,
        ),
    ]

    for index, group in enumerate(position_groups):
        raw_positions = group.get("positions")
        positions = raw_positions if isinstance(raw_positions, list) else []
        first_position: Mapping[str, object] = (
            positions[0]
            if positions and isinstance(positions[0], Mapping)
            else {}
        )
        group_key = (
            first_position.get("asset_type")
            or group.get("label")
            or str(index)
        )
        expected_capital_result = (
            Decimal(str(group.get("total_value") or 0))
            - Decimal(str(group.get("total_invested") or 0))
        )
        checks.append(
            build_reconciliation_check(
                f"groups.{group_key}.capital_result_value",
                expected_capital_result,
                group.get("capital_result_value"),
            )
        )

    serialized = [check.to_dict() for check in checks]
    failed_fields = [
        item["field"]
        for item in serialized
        if not item["is_reconciled"]
    ]
    return {
        "is_reconciled": not failed_fields,
        "valuation_mode": "intraday",
        "snapshot_evaluated": False,
        "money_tolerance": float(MONEY_TOLERANCE),
        "failed_fields": failed_fields,
        "checks": serialized,
        "source_contracts": [
            "summary.v2",
            "positions",
            "asset-distribution",
        ],
        "positions_groups_count": len(position_groups),
        "distribution_classes_count": len(asset_distribution),
    }


async def get_intraday_reconciliation(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Materializa os três contratos na mesma requisição e os reconcilia."""
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)
    position_groups = await get_canonical_portfolio_positions(db, portfolio_id, user_id)
    asset_distribution = await get_asset_distribution(db, portfolio_id, user_id)

    result = reconcile_intraday_consumers(
        summary,
        position_groups,
        asset_distribution,
    )
    result["portfolio_id"] = portfolio_id
    result["valuation_updated_at"] = summary.get("valuation_updated_at")
    return result
