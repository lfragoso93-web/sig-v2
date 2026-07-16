"""Fonte canonica para os KPIs consolidados de uma carteira.

O snapshot patrimonial mais recente e a fonte primaria dos valores financeiros.
A recomposicao por posicoes permanece apenas como contingencia explicita para
carteiras que ainda nao possuem snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.fixed_income_valuation_service import get_fixed_income_totals
from app.services.fx_service import get_usd_brl_today
from app.services.portfolio_service import (
    _MARKET_PRICE_TYPES,
    _cache_key,
    _non_fixed_income_enriched,
    get_portfolio,
    sum_dividends,
)
from app.services.realized_pnl_service import get_realized_pnl

_CACHE_TTL = 120


@dataclass(frozen=True, slots=True)
class PortfolioSummaryInput:
    """Valores consolidados necessarios para calcular os KPIs da carteira."""

    total_invested: float
    current_value: float
    dividends_12m: float = 0.0
    total_dividends: float = 0.0
    realized_pnl: float = 0.0
    has_partial_prices: bool = False
    assets_without_price: tuple[str, ...] = ()
    usd_brl_rate: float = 1.0
    accumulated_twr_pct: float | None = None
    daily_twr_pct: float | None = None


def build_portfolio_summary(data: PortfolioSummaryInput) -> dict:
    """Monta o contrato canonico de KPIs usado pelas telas financeiras.

    Semantica:
    - variacao: ganho ou perda nao realizada sobre o capital ainda empregado;
    - lucro total: nao realizado + realizado + historico integral de proventos;
    - rentabilidade total: TWR acumulado quando fornecido por snapshot;
    - fallback sem snapshot: lucro total sobre capital empregado;
    - total de proventos: historico integral recebido pela carteira.
    """
    total_invested = float(data.total_invested)
    current_value = float(data.current_value)
    unrealized_pnl = current_value - total_invested
    variation_pct = (
        unrealized_pnl / total_invested * 100
        if total_invested
        else 0.0
    )
    realized_pnl = float(data.realized_pnl)
    total_dividends = float(data.total_dividends)
    total_profit = unrealized_pnl + realized_pnl + total_dividends
    fallback_return_pct = (
        total_profit / total_invested * 100
        if total_invested
        else 0.0
    )
    total_return_pct = (
        float(data.accumulated_twr_pct)
        if data.accumulated_twr_pct is not None
        else fallback_return_pct
    )

    return {
        # Contrato canonico
        "total_patrimonio": round(current_value, 2),
        "total_investido": round(total_invested, 2),
        "lucro_total": round(total_profit, 2),
        "variacao_valor": round(unrealized_pnl, 2),
        "variacao_percentual": round(variation_pct, 4),
        "rentabilidade_total": round(total_return_pct, 4),
        "rentabilidade_acumulada": round(total_return_pct, 4),
        "rentabilidade_diaria": (
            round(float(data.daily_twr_pct), 6)
            if data.daily_twr_pct is not None
            else None
        ),
        "rentabilidade_source": (
            "snapshot_twr"
            if data.accumulated_twr_pct is not None
            else "valuation_fallback"
        ),
        "dividendos_recebidos_12m": round(float(data.dividends_12m), 2),
        "total_proventos": round(total_dividends, 2),
        "proventos_em_carteira": round(total_dividends, 2),
        "ganho_capital": round(unrealized_pnl, 2),
        "ganho_nao_realizado": round(unrealized_pnl, 2),
        "ganho_realizado": round(realized_pnl, 2),
        "has_partial_prices": bool(data.has_partial_prices),
        "assets_without_price": list(data.assets_without_price),
        "usd_brl_rate": round(float(data.usd_brl_rate), 4),
        # Aliases legados mantidos durante a migracao
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_gain": round(unrealized_pnl, 2),
        "total_gain_pct": round(variation_pct, 4),
    }


async def _get_latest_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> PortfolioSnapshot | None:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _build_summary_from_latest_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    snapshot: PortfolioSnapshot,
) -> dict:
    cutoff_12m = (datetime.now(timezone.utc) - timedelta(days=365)).date()
    dividends_12m = await sum_dividends(db, portfolio_id, cutoff=cutoff_12m)

    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=float(snapshot.cost_basis),
            current_value=float(snapshot.market_value),
            dividends_12m=dividends_12m,
            total_dividends=float(snapshot.dividends_accumulated),
            realized_pnl=float(snapshot.realized_pnl),
            has_partial_prices=bool(snapshot.has_partial_prices),
            usd_brl_rate=await get_usd_brl_today(db),
            accumulated_twr_pct=float(snapshot.accumulated_return_pct),
            daily_twr_pct=float(snapshot.daily_return_pct),
        )
    )
    summary.update(
        {
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "summary_source": "portfolio_snapshot",
            "return_is_estimated": bool(snapshot.return_is_estimated),
        }
    )
    return summary


async def _build_summary_from_valuation_fallback(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    enriched = await _non_fixed_income_enriched(db, portfolio_id)
    fixed_income = await get_fixed_income_totals(db, portfolio_id)

    non_fixed_invested = sum(position["total_invested"] for position in enriched)
    non_fixed_current = sum(
        position["current_value"]
        if position["current_value"] is not None
        else position["total_invested"]
        for position in enriched
    )

    total_invested = non_fixed_invested + float(fixed_income["invested_amount"])
    current_value = non_fixed_current + float(fixed_income["current_value"])

    assets_without_price = tuple(
        position["ticker"]
        for position in enriched
        if position.get("current_price") is None
        and position["asset_type"] in _MARKET_PRICE_TYPES
    )

    cutoff_12m = (datetime.now(timezone.utc) - timedelta(days=365)).date()
    dividends_12m = await sum_dividends(db, portfolio_id, cutoff=cutoff_12m)
    total_dividends = await sum_dividends(db, portfolio_id)
    realized_pnl = await get_realized_pnl(db, portfolio_id)

    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=total_invested,
            current_value=current_value,
            dividends_12m=dividends_12m,
            total_dividends=total_dividends,
            realized_pnl=realized_pnl,
            has_partial_prices=bool(assets_without_price),
            assets_without_price=assets_without_price,
            usd_brl_rate=await get_usd_brl_today(db),
        )
    )
    summary.update(
        {
            "snapshot_date": None,
            "summary_source": "valuation_fallback",
            "return_is_estimated": True,
        }
    )
    return summary


async def get_canonical_portfolio_summary(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna KPIs do snapshot mais recente ou contingencia sem snapshot."""
    await get_portfolio(db, portfolio_id, user_id)

    cache_key = _cache_key(portfolio_id, "summary")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    snapshot = await _get_latest_snapshot(db, portfolio_id)
    if snapshot is not None:
        summary = await _build_summary_from_latest_snapshot(db, portfolio_id, snapshot)
    else:
        summary = await _build_summary_from_valuation_fallback(db, portfolio_id)

    await cache_set(cache_key, summary, ttl=_CACHE_TTL)
    return summary
