from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IntradayReconciliationCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    expected: float
    observed: float
    difference: float
    tolerance: float
    is_reconciled: bool


class IntradayReconciliationResponse(BaseModel):
    """Reconciliação entre consumidores da mesma referência intradiária."""

    model_config = ConfigDict(extra="forbid")

    portfolio_id: int
    valuation_mode: Literal["intraday"]
    valuation_updated_at: str | None
    snapshot_evaluated: Literal[False]
    money_tolerance: float = Field(ge=0)
    is_reconciled: bool
    failed_fields: list[str]
    checks: list[IntradayReconciliationCheckResponse]
    source_contracts: list[str]
    positions_groups_count: int = Field(ge=0)
    distribution_classes_count: int = Field(ge=0)
