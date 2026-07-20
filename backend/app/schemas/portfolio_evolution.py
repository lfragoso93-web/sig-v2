from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class PortfolioDailyEvolutionResponse(BaseModel):
    """Contrato do histórico diário consolidado materializado."""

    model_config = ConfigDict(extra="forbid")

    date: str
    market_value: float
    cost_basis: float
    invested_total: float
    net_external_flow: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_pct: float
    dividends_day: float
    dividends_accumulated: float
    daily_return_pct: float
    accumulated_return_pct: float
    has_partial_prices: bool
    return_is_estimated: bool
    history_source: Literal["portfolio_snapshot"]


class PortfolioMonthlyEvolutionResponse(PortfolioDailyEvolutionResponse):
    """Contrato do último fechamento e TWR composto de cada mês."""

    value: float
    invested: float
    period: str
    monthly_return_pct: float


class PortfolioClassDailyEvolutionResponse(BaseModel):
    """Contrato do histórico diário materializado por classe."""

    model_config = ConfigDict(extra="forbid")

    asset_type: str
    date: str
    market_value: float
    cost_basis: float
    realized_pnl: float
    unrealized_pnl: float
    net_external_flow: float
    dividends_day: float
    dividends_accumulated: float
    daily_return_pct: float
    accumulated_return_pct: float
    has_partial_prices: bool
    return_is_estimated: bool
    valuation_status: Literal["complete", "partial_prices"]
    history_source: Literal["portfolio_class_snapshot"]


class PortfolioClassMonthlyEvolutionResponse(PortfolioClassDailyEvolutionResponse):
    """Contrato do último fechamento e TWR mensal por classe."""

    period: str
    monthly_return_pct: float


class PortfolioClassAvailabilityResponse(BaseModel):
    """Disponibilidade real do motor e dos dados históricos por classe."""

    model_config = ConfigDict(extra="forbid")

    asset_type: str
    available: bool
    engine_supported: bool
    data_available: bool
    latest_snapshot_date: str | None
    status: Literal[
        "available",
        "awaiting_backfill",
        "dedicated_history_not_available",
    ]
    reason: str | None


class PortfolioClassReconciliationCheckResponse(BaseModel):
    """Comparação monetária entre consolidado e soma das classes."""

    model_config = ConfigDict(extra="forbid")

    field: Literal[
        "market_value",
        "cost_basis",
        "net_external_flow",
        "dividends_day",
    ]
    expected: float
    observed: float
    difference: float
    tolerance: float
    is_reconciled: bool


class PortfolioClassReconciliationResponse(BaseModel):
    """Contrato da reconciliação do fechamento mais recente."""

    model_config = ConfigDict(extra="forbid")

    is_reconciled: bool | None
    is_comparable: bool
    status: Literal[
        "evaluated",
        "missing_class_snapshots",
        "missing_portfolio_snapshot",
        "not_comparable_unsupported_classes",
    ]
    unsupported_asset_types: list[str]
    snapshot_date: str | None
    checks: list[PortfolioClassReconciliationCheckResponse]
