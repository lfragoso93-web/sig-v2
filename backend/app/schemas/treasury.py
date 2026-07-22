"""
Schemas de resposta para Tesouro Direto.

Como o Tesouro e gerenciado via transactions, nao ha schema de Create/Update
dedicado. O dado entra pelo endpoint padrao de transactions.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class TreasuryPositionResponse(BaseModel):
    """Representa um lote de compra de Tesouro Direto enriquecido com cotacao."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    brapi_name: str
    ticker: str
    purchase_price: float
    quantity: float
    invested_value: float
    purchase_date: Optional[str] = None
    maturity_date: Optional[str] = None
    is_active: bool = True
    current_price: Optional[float] = None
    valor_atual: Optional[float] = None
    lucro_prejuizo: Optional[float] = None
    rentabilidade_pct: Optional[float] = None
    quantidade_cotas: Optional[float] = None
    notes: Optional[str] = None
