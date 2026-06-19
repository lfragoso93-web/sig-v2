"""
Schemas de posicao alinhados com o contrato do portfolio_service
(calc_raw_positions + enrich_with_prices).

Nao depende do model Position legado nem de PortfolioPosition diretamente -
recebe dicionarios do service e os valida via Pydantic.
"""
from pydantic import BaseModel
from typing import Optional


class PositionOut(BaseModel):
    """
    Posicao individual de um ativo na carteira, enriquecida com preco atual.
    current_price, current_value, variation_value e variation_percent sao
    None quando cotacao nao esta disponivel — permite ao frontend diferenciar
    "sem cotacao" de "resultado zero".
    """
    id:                Optional[int]   = None   # id sintetico para chave React
    ticker:            str
    asset_type:        str
    asset_label:       str
    quantity:          float
    average_price:     float
    current_price:     Optional[float] = None   # None = sem cotacao
    current_value:     Optional[float] = None   # None = sem cotacao
    invested_value:    float
    variation_value:   Optional[float] = None   # None = sem cotacao
    variation_percent: Optional[float] = None   # None = sem cotacao
    allocation_pct:    float


class AssetGroupOut(BaseModel):
    """
    Grupo de posicoes por tipo de ativo (ex: Acoes, FIIs).
    """
    label:       str
    count:       int
    total_value: float
    positions:   list[PositionOut] = []


class PortfolioSummary(BaseModel):
    """
    Resumo consolidado da carteira retornado por /positions/summary.
    Alinhado com get_portfolio_summary() do portfolio_service.

    rentabilidade_total = (lucro_total / total_invested * 100)
    onde lucro_total = ganho_capital + total_proventos.
    variacao_percentual = (variacao_valor / total_invested * 100) — so capital.
    """
    total_invested:           float
    current_value:            float
    total_gain:               float
    total_gain_pct:           float
    total_patrimonio:         float
    total_investido:          float
    lucro_total:              float
    variacao_valor:           float
    variacao_percentual:      float
    rentabilidade_total:      float
    dividendos_recebidos_12m: float
    total_proventos:          float
    ganho_capital:            float


# Alias mantido para imports existentes em outros modulos
PositionResponse = PositionOut
