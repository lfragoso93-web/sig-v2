"""Schemas finais da página Rentabilidade."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class RentabilidadeKpisResponse(BaseModel):
    """Contrato canônico dos KPIs financeiros e de TWR."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["rentabilidade.v2"] = "rentabilidade.v2"

    patrimonio_atual: float
    custo_posicoes_abertas: float
    resultado_nao_realizado: float
    resultado_realizado: float
    resultado_total: float
    proventos_total: float
    proventos_12m: float

    twr_dia_pct: float | None
    twr_mes_pct: float | None
    twr_12m_pct: float | None
    twr_desde_inicio_pct: float | None

    valuation_updated_at: str | None
    performance_as_of: str | None
    proventos_as_of: str | None
    return_is_estimated: bool
    has_partial_prices: bool
    price_coverage_pct: float
    performance_source: Literal["portfolio_snapshot_twr", "unavailable"]
