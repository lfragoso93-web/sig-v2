"""
Schemas de posicao alinhados com o contrato do portfolio_service
(calc_raw_positions + enrich_with_prices).
"""
from pydantic import BaseModel
from typing import Optional


class PositionOut(BaseModel):
    """
    Posicao individual de um ativo na carteira, enriquecida com preco atual.
    current_price, current_value, variation_value e variation_percent sao
    None quando cotacao nao esta disponivel.
    logo_url e None enquanto o onboarding nao foi executado para o ativo.
    """
    id:                Optional[int]   = None
    ticker:            str
    asset_type:        str
    asset_label:       str
    quantity:          float
    average_price:     float
    current_price:     Optional[float] = None
    current_value:     Optional[float] = None
    invested_value:    float
    variation_value:   Optional[float] = None
    variation_percent: Optional[float] = None
    allocation_pct:    float
    logo_url:          Optional[str]   = None


class AssetGroupOut(BaseModel):
    """
    Grupo de posicoes por tipo de ativo (ex: Acoes, FIIs).
    Inclui total_invested, variation_pct, rentabilidade_pct e target_pct quando disponiveis.

    rentabilidade_pct: variacao de capital do grupo em %. None enquanto nao houver
    calculo de proventos por grupo (sprint futura).
    """
    label:             str
    count:             int
    total_value:       float
    total_invested:    Optional[float] = None
    variation_pct:     Optional[float] = None
    rentabilidade_pct: Optional[float] = None
    target_pct:        Optional[float] = None
    positions:         list[PositionOut] = []


class PortfolioSummary(BaseModel):
    """
    Resumo consolidado da carteira retornado por /positions/summary.
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


# ── Schemas para metas por classe ─────────────────────────────────────────────────────────────────────────────────
class ClassTargetOut(BaseModel):
    asset_type: str
    target_pct: float


class ClassTargetIn(BaseModel):
    target_pct: float
