"""Contrato interno versionado da apuração anual canônica de IRPF."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

IRPF_ANNUAL_ASSESSMENT_SCHEMA_VERSION = "irpf-annual-assessment.v1"


@dataclass(frozen=True)
class IrpfMonthlyAssessmentContract:
    competence_month: str
    swing_gross_tax_due_brl: Decimal
    swing_withholding_brl: Decimal
    swing_net_tax_due_brl: Decimal
    day_trade_gross_tax_due_brl: Decimal
    day_trade_withholding_brl: Decimal
    day_trade_net_tax_due_brl: Decimal
    total_net_tax_due_brl: Decimal
    payment_due_brl: Decimal
    closing_accumulated_tax_brl: Decimal


@dataclass(frozen=True)
class IrpfAnnualAssessmentContract:
    schema_version: str
    portfolio_id: int
    year: int
    monthly: tuple[IrpfMonthlyAssessmentContract, ...]
    total_gross_tax_due_brl: Decimal
    total_withholding_brl: Decimal
    total_net_tax_due_brl: Decimal
    total_payment_due_brl: Decimal
    closing_accumulated_tax_brl: Decimal
    closing_common_withholding_balance_brl: Decimal
    closing_day_trade_withholding_balance_brl: Decimal
    closing_day_trade_loss_carryforward_brl: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Serializa o contrato preservando Decimal para consumidores internos."""

        return asdict(self)
