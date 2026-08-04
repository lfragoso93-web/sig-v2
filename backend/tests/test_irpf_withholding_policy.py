"""Testes da política canônica de IRRF em renda variável."""

from decimal import Decimal

import pytest
from app.services.irpf_withholding_policy import (
    WithholdingOperationKind,
    assess_common_withholding,
    assess_day_trade_withholding,
)


def test_common_withholding_uses_gross_sales_base() -> None:
    assessment = assess_common_withholding(
        competence_month="2024-05",
        gross_sales_brl=Decimal("60000.00"),
    )

    assert assessment.operation_kind is WithholdingOperationKind.COMMON
    assert assessment.calculation_base_brl == Decimal("60000.00")
    assert assessment.withholding_rate == Decimal("0.00005")
    assert assessment.withholding_tax_brl == Decimal("3.00")


def test_day_trade_withholding_uses_positive_net_result() -> None:
    assessment = assess_day_trade_withholding(
        competence_month="2024-05",
        net_day_trade_result_brl=Decimal("250.00"),
    )

    assert assessment.operation_kind is WithholdingOperationKind.DAY_TRADE
    assert assessment.calculation_base_brl == Decimal("250.00")
    assert assessment.withholding_rate == Decimal("0.01")
    assert assessment.withholding_tax_brl == Decimal("2.50")


def test_day_trade_loss_does_not_generate_withholding() -> None:
    assessment = assess_day_trade_withholding(
        competence_month="2024-05",
        net_day_trade_result_brl=Decimal("-250.00"),
    )

    assert assessment.calculation_base_brl == Decimal("0.00")
    assert assessment.withholding_tax_brl == Decimal("0.00")


def test_withholding_rounds_half_up_to_cents() -> None:
    assessment = assess_common_withholding(
        competence_month="2024-05",
        gross_sales_brl=Decimal("50100.00"),
    )

    assert assessment.withholding_tax_brl == Decimal("2.51")


def test_common_withholding_rejects_negative_sales() -> None:
    with pytest.raises(ValueError, match="valor bruto de vendas não pode ser negativo"):
        assess_common_withholding(
            competence_month="2024-05",
            gross_sales_brl=Decimal("-1.00"),
        )
