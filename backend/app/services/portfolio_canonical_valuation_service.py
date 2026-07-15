"""Composição canônica do valuation diário da carteira.

Mantém o valuation legado para ativos de mercado e substitui somente o componente
Renda Fixa pelo motor dedicado baseado em benchmarks persistidos. A integração é
incremental para permitir comparação segura dos snapshots antes/depois.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    _aggregate_applications,
    _apply_redemption,
    _application_from_buy,
    _is_buy,
    _is_sell,
)
from app.services.portfolio_snapshot_service import _calc_totals as _legacy_calc_totals

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_PCT = Decimal("0.0001")


async def _fixed_income_totals_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, Decimal]:
    """Calcula Renda Fixa usando somente lançamentos existentes até a data-alvo."""
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_type == RENDA_FIXA_TYPE,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )

    applications = []
    for tx in result.scalars().all():
        if _is_buy(tx.operation):
            application = _application_from_buy(tx)
            if application.invested_amount > 0:
                applications.append(application)
        elif _is_sell(tx.operation):
            _apply_redemption(applications, tx)

    valuations = await _aggregate_applications(db, applications, target_date)
    invested = sum((item.invested_amount for item in valuations), _ZERO).quantize(_MONEY)
    current = sum((item.current_value for item in valuations), _ZERO).quantize(_MONEY)
    return {
        "invested_amount": invested,
        "current_value": current,
        "income_amount": (current - invested).quantize(_MONEY),
    }


async def calculate_canonical_portfolio_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict:
    """Retorna os totais legados corrigidos pelo valuation dedicado de Renda Fixa.

    O motor legado avalia Renda Fixa pelo custo médio quando não encontra cotação.
    Portanto, substituímos esse componente pelo saldo corrigido sem alterar o custo
    contábil ou o fluxo líquido histórico da carteira.
    """
    totals = await _legacy_calc_totals(db, portfolio_id, target_date)
    fixed_income = await _fixed_income_totals_at_date(db, portfolio_id, target_date)

    correction = fixed_income["current_value"] - fixed_income["invested_amount"]
    market_value = Decimal(str(totals["market_value"])) + correction
    unrealized_pnl = Decimal(str(totals["unrealized_pnl"])) + correction
    realized_pnl = Decimal(str(totals["realized_pnl"]))
    total_pnl = realized_pnl + unrealized_pnl
    cost_basis = Decimal(str(totals["cost_basis"]))
    invested_total = Decimal(str(totals["invested_total"]))

    return_base = cost_basis + max(realized_pnl, _ZERO)
    if return_base > 0:
        return_pct = total_pnl / return_base * Decimal("100")
    elif invested_total > 0:
        return_pct = total_pnl / invested_total * Decimal("100")
    else:
        return_pct = _ZERO

    return {
        **totals,
        "market_value": market_value.quantize(_MONEY),
        "unrealized_pnl": unrealized_pnl.quantize(_MONEY),
        "total_pnl": total_pnl.quantize(_MONEY),
        "return_pct": return_pct.quantize(_PCT),
        "fixed_income_invested": fixed_income["invested_amount"],
        "fixed_income_current": fixed_income["current_value"],
        "fixed_income_income": fixed_income["income_amount"],
    }
