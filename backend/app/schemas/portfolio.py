"""
Schemas de portfolio, metas de alocacao e view combinada alvo vs atual.

Alteracoes Sprint 5E:
- ClassTargetWithCurrent: novo schema para endpoint targets-with-current

Fix 2026-06-30:
- Adicionado alias PortfolioResponse = PortfolioRead para compatibilidade
  com router que importa PortfolioResponse.
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
import datetime


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------
class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None


class PortfolioRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Alias para compatibilidade com routers que importam PortfolioResponse
PortfolioResponse = PortfolioRead


# ---------------------------------------------------------------------------
# Metas por classe
# ---------------------------------------------------------------------------
class ClassTargetUpsert(BaseModel):
    asset_type: str
    target_pct: float = Field(..., ge=0, le=100)


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------
class CSVRowValidation(BaseModel):
    row_num: int
    errors: list[str] = []
    warnings: list[str] = []
    status: str
    ticker: Optional[str] = None
    operation: Optional[str] = None
    quantity: Optional[float] = None


class CSVImportResponse(BaseModel):
    success: bool
    imported_count: int
    skipped_count: int
    error_count: int
    rows: list[CSVRowValidation] = []
    global_errors: list[str] = []


class ClassTargetRead(BaseModel):
    id: int
    portfolio_id: int
    asset_type: str
    target_pct: Decimal

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Sprint 5E: alvo vs atual combinado
# ---------------------------------------------------------------------------
class ClassTargetWithCurrent(BaseModel):
    """
    Retornado pelo endpoint GET /portfolios/{id}/targets-with-current.
    Combina a distribuicao atual da carteira com as metas configuradas.
    Inclui BDR explicitamente (Sprint 5E - Issue #79).
    """
    asset_type: str
    label: str
    target_pct: float = Field(description="Meta configurada (0 se nao definida)")
    current_pct: float = Field(description="Percentual atual da carteira")
    delta_pct: float   = Field(description="current_pct - target_pct")
    color: str         = Field(description="Cor hex para uso no grafico")

    class Config:
        from_attributes = True
