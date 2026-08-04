"""Testes da compensação mensal e segregada de IRRF."""

from decimal import Decimal

import pytest
from app.services.irpf_withholding_compensation import compensate_withholding
from app.services.irpf_withholding_policy import WithholdingOperationKind


def test_withholding_fully_offsets_monthly_tax() -> None:
    result = compensate_withholding(
        competence_month="2024-01",
        operation_kind=WithholdingOperationKind.COMMON,
        gross_tax_due_brl=Decimal("10.00"),
        current_withholding_brl=Decimal("12.00"),
    )

    assert result.withholding_used_brl == Decimal("10.00")
    assert result.closing_withholding_balance_brl == Decimal("2.00")
    assert result.net_tax_due_brl == Decimal("0.00")


def test_withholding_partially_offsets_monthly_tax() -> None:
    result = compensate_withholding(
        competence_month="2024-02",
        operation_kind=WithholdingOperationKind.DAY_TRADE,
        gross_tax_due_brl=Decimal("20.00"),
        current_withholding_brl=Decimal("3.50"),
    )

    assert result.withholding_used_brl == Decimal("3.50")
    assert result.closing_withholding_balance_brl == Decimal("0.00")
    assert result.net_tax_due_brl == Decimal("16.50")


def test_opening_balance_is_consumed_before_carrying_remainder() -> None:
    result = compensate_withholding(
        competence_month="2024-03",
        operation_kind=WithholdingOperationKind.COMMON,
        gross_tax_due_brl=Decimal("8.00"),
        current_withholding_brl=Decimal("1.00"),
        opening_withholding_balance_brl=Decimal("10.00"),
    )

    assert result.withholding_used_brl == Decimal("8.00")
    assert result.closing_withholding_balance_brl == Decimal("3.00")
    assert result.net_tax_due_brl == Decimal("0.00")


def test_operation_kind_is_preserved_for_bucket_segregation() -> None:
    common = compensate_withholding(
        competence_month="2024-04",
        operation_kind=WithholdingOperationKind.COMMON,
        gross_tax_due_brl=Decimal("5.00"),
        current_withholding_brl=Decimal("1.00"),
    )
    day_trade = compensate_withholding(
        competence_month="2024-04",
        operation_kind=WithholdingOperationKind.DAY_TRADE,
        gross_tax_due_brl=Decimal("5.00"),
        current_withholding_brl=Decimal("1.00"),
    )

    assert common.operation_kind is WithholdingOperationKind.COMMON
    assert day_trade.operation_kind is WithholdingOperationKind.DAY_TRADE


def test_negative_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="IRRF do mês não pode ser negativo"):
        compensate_withholding(
            competence_month="2024-05",
            operation_kind=WithholdingOperationKind.COMMON,
            gross_tax_due_brl=Decimal("1.00"),
            current_withholding_brl=Decimal("-0.01"),
        )
