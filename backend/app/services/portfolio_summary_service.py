"""Fonte canonica para os KPIs consolidados de uma carteira.

Este modulo concentra a semantica financeira exibida em Resumo, Patrimonio e
futuros consumidores. A coleta de posicoes, cotacoes, renda fixa e proventos
pode continuar em servicos especializados; a composicao final dos indicadores
deve passar por ``build_portfolio_summary``.
"""
from __future__ import annotations

from dataclasses import dataclass


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
