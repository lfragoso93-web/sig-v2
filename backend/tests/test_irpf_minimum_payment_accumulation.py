"""Testes da acumulação configurável de imposto mínimo."""

from decimal import Decimal

import pytest
from app.services.irpf_minimum_payment_accumulation import (
    assess_minimum_payment,
    assess_minimum_payments,
)


def test_amount_below_threshold_is_carried_forward() -> None:
    result = assess_minimum_payment(
        competence_month="2024-01",
        current_net_tax_due_brl=Decimal("4.00"),
        minimum_payment_threshold_brl=Decimal("10.00"),
    )

    assert result.payment_due_brl == Decimal("0.00")
    assert result.closing_accumulated_tax_brl == Decimal("4.00")


def test_exact_threshold_becomes_payable() -> None:
    result = assess_minimum_payment(
        competence_month="2024-02",
        current_net_tax_due_brl=Decimal("6.00"),
        opening_accumulated_tax_brl=Decimal("4.00"),
        minimum_payment_threshold_brl=Decimal("10.00"),
    )

    assert result.accumulated_tax_before_payment_brl == Decimal("10.00")
    assert result.payment_due_brl == Decimal("10.00")
    assert result.closing_accumulated_tax_brl == Decimal("0.00")


def test_amount_above_threshold_becomes_payable() -> None:
    result = assess_minimum_payment(
        competence_month="2024-03",
        current_net_tax_due_brl=Decimal("12.345"),
        minimum_payment_threshold_brl=Decimal("10.00"),
    )

    assert result.payment_due_brl == Decimal("12.35")
    assert result.closing_accumulated_tax_brl == Decimal("0.00")


def test_monthly_sequence_is_sorted_and_balance_is_transported() -> None:
    result = assess_minimum_payments(
        monthly_net_tax_due=[
            ("2024-03", Decimal("1.00")),
            ("2024-01", Decimal("4.00")),
            ("2024-02", Decimal("6.00")),
        ],
        minimum_payment_threshold_brl=Decimal("10.00"),
    )

    assert [item.competence_month for item in result] == [
        "2024-01",
        "2024-02",
        "2024-03",
    ]
    assert result[0].closing_accumulated_tax_brl == Decimal("4.00")
    assert result[1].payment_due_brl == Decimal("10.00")
    assert result[2].opening_accumulated_tax_brl == Decimal("0.00")
    assert result[2].closing_accumulated_tax_brl == Decimal("1.00")


def test_invalid_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="limite mínimo de pagamento deve ser positivo"):
        assess_minimum_payment(
            competence_month="2024-01",
            current_net_tax_due_brl=Decimal("1.00"),
            minimum_payment_threshold_brl=Decimal("0.00"),
        )
