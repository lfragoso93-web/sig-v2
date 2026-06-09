from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from enum import Enum


class DividendType(str, Enum):
    dividendo   = "dividendo"
    jcp         = "jcp"
    rendimento  = "rendimento"
    amortizacao = "amortizacao"
    outro       = "outro"


class DividendCreate(BaseModel):
    ticker:       str
    asset_type:   str
    type:         DividendType
    amount:       float = Field(gt=0, description="Valor por cota")
    quantity:     float = Field(gt=0, description="Quantidade de cotas")
    payment_date: date
    ex_date:      Optional[date] = None


class DividendOut(BaseModel):
    id:           int
    portfolio_id: int
    ticker:       str
    asset_type:   str
    type:         DividendType
    amount:       float
    quantity:     float
    payment_date: date
    ex_date:      Optional[date]

    class Config:
        from_attributes = True


class MonthPoint(BaseModel):
    month:  str
    amount: float


class DividendSummary(BaseModel):
    total_received:  float
    total_projected: float
    monthly:         List[MonthPoint]


# ── Schemas de Proventos ──────────────────────────────────────────────────────

class ProventosSummary(BaseModel):
    total_recebido:    float
    total_projetado:   float
    media_mensal:      float
    yield_medio:       Optional[float] = None


class ProventoDistribution(BaseModel):
    ticker:     str
    asset_type: str
    total:      float
    percentual: float


class ProventosEvolucao(BaseModel):
    periodo:    str
    total:      float
    acoes:      float = 0.0
    fiis:       float = 0.0
    outros:     float = 0.0


class ProventosHistoricoMes(BaseModel):
    mes:        str
    total:      float
    status:     Optional[str] = None


class ProventoItem(BaseModel):
    id:           int
    portfolio_id: int
    ticker:       str
    asset_type:   str
    type:         DividendType
    amount:       float
    quantity:     float
    total:        float
    payment_date: date
    ex_date:      Optional[date] = None
    status:       Optional[str] = None

    class Config:
        from_attributes = True
