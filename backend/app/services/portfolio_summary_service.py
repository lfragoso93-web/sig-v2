"""Fonte canonica para os KPIs consolidados de uma carteira.

Este modulo concentra a semantica financeira exibida em Resumo, Patrimonio e
futuros consumidores. A coleta de posicoes, cotacoes, renda fixa e proventos
continua em servicos especializados; a composicao final dos indicadores passa
por ``build_portfolio_summary``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.services.fixed_income_valuation_service import get_fixed_income_totals
from app.services.fx_service import get_usd_brl_today
from app.services.portfolio_service import (
    _MARKET_PRICE_TYPES,
    _cache_key,
    _non_fixed_income_enriched,
    get_portfolio,
    sum_dividends,
    sum_dividends_for_tickers,
)

_CACHE_TTL = 120


@dataclass(frozen=True, slots=True)
class PortfolioSummaryInput:
    """Valores consolidados necessarios para calcular os KPIs da carteira."""

    total_invested: float
    current_value: float
    dividends_12m: float = 0.0
    total_dividends: float = 0.0
    active_position_dividends: float = 0.0
    has_partial_prices: bool = False
    assets_without_price: tuple[str, ...] = ()
    usd_brl_rate: float = 1.0


def build_portfolio_summary(data: PortfolioSummaryInput) -> dict:
    """Monta o contrato canonico de KPIs usado pelas telas financeiras.

    Semantica:
    - variacao: ganho ou perda atual de preco sobre o capital ainda empregado;
    - lucro total: variacao atual + proventos dos ativos ainda em carteira;
    - rentabilidade total: lucro total dividido pelo capital empregado;
    - total de proventos: historico integral recebido pela carteira.
    """
    total_invested = float(data.total_invested)
    current_value = float(data.current_value)
    variation_value = current_value - total_invested
    variation_pct = (
        variation_value / total_invested * 100
        if total_invested
        else 0.0
    )
    total_profit = variation_value + float(data.active_position_dividends)
    total_return_pct = (
        total_profit / total_invested * 100
        if total_invested
        else 0.0
    )

    return {
        # Contrato canonico
        "total_patrimonio": round(current_value, 2),
        "total_investido": round(total_invested, 2),
        "lucro_total": round(total_profit, 2),
        "variacao_valor": round(variation_value, 2),
        "variacao_percentual": round(variation_pct, 4),
        "rentabilidade_total": round(total_return_pct, 4),
        "dividendos_recebidos_12m": round(float(data.dividends_12m), 2),
        "total_proventos": round(float(data.total_dividends), 2),
        "proventos_em_carteira": round(float(data.active_position_dividends), 2),
        "ganho_capital": round(variation_value, 2),
        "has_partial_prices": bool(data.has_partial_prices),
        "assets_without_price": list(data.assets_without_price),
        "usd_brl_rate": round(float(data.usd_brl_rate), 4),
        # Aliases legados mantidos durante a migracao
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_gain": round(variation_value, 2),
        "total_gain_pct": round(variation_pct, 4),
    }


async def get_canonical_portfolio_summary(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Coleta os dados especializados e retorna o resumo financeiro canonico."""
    await get_portfolio(db, portfolio_id, user_id)

    cache_key = _cache_key(portfolio_id, "summary")
    cached = await cache_get(cache_key)
    if cached:
        return cached

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

    active_tickers = [position["ticker"] for position in enriched]
    active_position_dividends = await sum_dividends_for_tickers(
        db,
        portfolio_id,
        active_tickers,
    )

    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=total_invested,
            current_value=current_value,
            dividends_12m=dividends_12m,
            total_dividends=total_dividends,
            active_position_dividends=active_position_dividends,
            has_partial_prices=bool(assets_without_price),
            assets_without_price=assets_without_price,
            usd_brl_rate=await get_usd_brl_today(db),
        )
    )

    await cache_set(cache_key, summary, ttl=_CACHE_TTL)
    return summary
