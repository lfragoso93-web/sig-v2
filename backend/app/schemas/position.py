"""
Schemas de posicao alinhados com o contrato do portfolio_service
(calc_raw_positions + enrich_with_prices).

Nao depende do model Position legado nem de PortfolioPosition diretamente —
recebe dicionarios do service e os valida via Pydantic.
"""
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional


class PositionOut(BaseModel):
    """
    Posicao individual de um ativo na carteira, enriquecida com preco atual.
    Campos de preco/variacao sao None quando cotacao nao esta disponivel.
    """
    ticker:           str
    asset_type:       str
    asset_label:      str
    quantity:         float
    average_price:    float
    current_price:    Optional[float] = None
    current_value:    float
    invested_value:   float
    variation_value:  float
    variation_percent: float
    allocation_pct:   float


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
