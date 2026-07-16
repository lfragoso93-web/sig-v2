from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PortfolioSummaryResponse(BaseModel):
    """Contrato público e versionado da página Resumo."""

    model_config = ConfigDict(extra="forbid")

    summary_version: Literal["summary.v2"]

    total_patrimonio: float
    total_investido: float
    lucro_total: float
    variacao_valor: float
    variacao_percentual: float
    ganho_nao_realizado: float
    ganho_realizado: float

    rentabilidade_total: float
    rentabilidade_acumulada: float
    rentabilidade_diaria: float | None
    rentabilidade_source: Literal["snapshot_twr", "valuation_fallback"]

    dividendos_recebidos_12m: float
    total_proventos: float
    proventos_as_of: str
    proventos_source: Literal["received_cash_dividends"]

    has_partial_prices: bool
    assets_without_price: list[str]
    price_assets_total: int = Field(ge=0)
    price_assets_covered: int = Field(ge=0)
    price_coverage_pct: float = Field(ge=0, le=100)

    usd_brl_rate: float
    valuation_mode: Literal["intraday"]
    valuation_updated_at: str | None
    performance_as_of: str | None
    snapshot_id: int | None
    snapshot_date: str | None
    summary_source: Literal[
        "intraday_valuation_with_snapshot_twr",
        "valuation_fallback",
    ]
    return_is_estimated: bool

    is_reconciled: bool | None
    reconciliation: dict[str, Any] | None
