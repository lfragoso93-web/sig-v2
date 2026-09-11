"""Expectativas fiscais independentes para a carteira sintética da Issue #303.

Os valores abaixo são derivados do fixture certificado e dos contratos fiscais
internos vigentes. Este módulo não importa serviços de IRPF nem ORM e existe
somente como oráculo de certificação.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict


class SyntheticDisposalExpectation(TypedDict):
    gross_proceeds_brl: Decimal
    cost_basis_brl: Decimal
    fees_brl: Decimal
    realized_pnl_brl: Decimal
    fiscal_group: str
    exemption_applied: bool


@dataclass(frozen=True)
class SyntheticIrpfExpectation:
    year: int
    disposal_count: int
    total_common_gross_sales_brl: Decimal
    total_swing_realized_pnl_brl: Decimal
    total_swing_taxable_base_brl: Decimal
    total_swing_tax_due_brl: Decimal
    common_withholding_brl: Decimal
    total_swing_net_tax_due_brl: Decimal
    total_payment_due_brl: Decimal
    total_day_trade_result_brl: Decimal
    total_day_trade_tax_due_brl: Decimal


EXPECTED_SYNTHETIC_IRPF_2026 = SyntheticIrpfExpectation(
    year=2026,
    disposal_count=2,
    total_common_gross_sales_brl=Decimal("3700.00"),
    total_swing_realized_pnl_brl=Decimal("450.80"),
    total_swing_taxable_base_brl=Decimal("198.00"),
    total_swing_tax_due_brl=Decimal("29.70"),
    common_withholding_brl=Decimal("0.19"),
    total_swing_net_tax_due_brl=Decimal("29.51"),
    total_payment_due_brl=Decimal("29.51"),
    total_day_trade_result_brl=Decimal("0.00"),
    total_day_trade_tax_due_brl=Decimal("0.00"),
)

EXPECTED_DISPOSALS_2026: dict[str, SyntheticDisposalExpectation] = {
    "CERT303-PETR4": {
        "gross_proceeds_brl": Decimal("1500.00"),
        "cost_basis_brl": Decimal("1243.20"),
        "fees_brl": Decimal("4.00"),
        "realized_pnl_brl": Decimal("252.80"),
        "fiscal_group": "stocks",
        "exemption_applied": True,
    },
    "CERT303-BOVA11": {
        "gross_proceeds_brl": Decimal("2200.00"),
        "cost_basis_brl": Decimal("2001.00"),
        "fees_brl": Decimal("1.00"),
        "realized_pnl_brl": Decimal("198.00"),
        "fiscal_group": "etf",
        "exemption_applied": False,
    },
}
