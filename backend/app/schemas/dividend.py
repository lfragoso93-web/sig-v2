from pydantic import BaseModel
from typing import Optional
from datetime import date
from enum import Enum


class DividendStatus(str, Enum):
    RECEBIDO = "RECEBIDO"
    A_RECEBER = "A_RECEBER"


class DividendType(str, Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    BONIFICACAO = "BONIFICACAO"
    OUTROS = "OUTROS"


class ProventosSummary(BaseModel):
    media_mensal: float
    meta_mensal: float
    meta_percent: float
    total_12m: float
    total_carteira: float


class ProventoDistribution(BaseModel):
    ticker: str
    total: float
    percentage: float


class ProventosEvolucao(BaseModel):
    month: str
    recebido: float
    a_receber: float


class ProventosHistoricoMes(BaseModel):
    year: int
    months: list[Optional[float]]
    total: float
    media: float


class ProventoItem(BaseModel):
    id: int
    ticker: str
    asset_type: str
    dividend_type: str
    status: str
    ex_date: date
    payment_date: Optional[date]
    quantity: float
    value_per_unit: float
    total_value: float
    net_value: float

    class Config:
        from_attributes = True
