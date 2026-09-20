"""Contrato compartilhado para resolu??o fracion?ria de eventos corporativos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class FractionalResolutionPolicy(StrEnum):
    NO_FRACTIONAL_RESIDUE = "NO_FRACTIONAL_RESIDUE"
    CASH_SETTLEMENT = "CASH_SETTLEMENT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass(frozen=True)
class FractionalResolution:
    policy: FractionalResolutionPolicy
    fractional_quantity: Decimal | None = None
    settlement_price: Decimal | None = None
    cash_treatment: str | None = None
