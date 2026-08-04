"""Testes do contrato interno versionado da apuração anual de IRPF."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.irpf_annual_assessment_contract import (
    IRPF_ANNUAL_ASSESSMENT_SCHEMA_VERSION,
)
from app.services.irpf_annual_assessment_contract_mapper import (
    build_irpf_annual_assessment_contract,
)
from app.services.irpf_withholding_policy import WithholdingOperationKind


def _withholding(
    *,
    month: str,
    kind: WithholdingOperationKind,
    gross: str,
    current: str,
    used: str,
    net: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        competence_month=month,
        operation_kind=kind,
        gross_tax_due_brl=Decimal(gross),
        current_withholding_brl=Decimal(current),
        opening_withholding_balance_brl=Decimal("0.00"),
        withholding_used_brl=Decimal(used),
        closing_withholding_balance_brl=Decimal("0.00"),
        net_tax_due_brl=Decimal(net),
    )


def test_mapper_builds_versioned_monthly_contract() -> None:
    assessment = SimpleNamespace(
        portfolio_id=7,
        year=2024,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        swing=SimpleNamespace(
            monthly=(
                SimpleNamespace(competence_month="2024-02", tax_due_brl=Decimal("4.50")),
                SimpleNamespace(competence_month="2024-01", tax_due_brl=Decimal("1.50")),
            )
        ),
        common_withholding_monthly=(
            _withholding(
                month="2024-01",
                kind=WithholdingOperationKind.COMMON,
                gross="1.50",
                current="0.10",
                used="0.10",
                net="1.40",
            ),
            _withholding(
                month="2024-02",
                kind=WithholdingOperationKind.COMMON,
                gross="4.50",
                current="0.20",
                used="0.20",
                net="4.30",
            ),
        ),
        day_trade_monthly=(
            SimpleNamespace(competence_month="2024-02", tax_due_brl=Decimal("2.00")),
        ),
        day_trade_withholding_monthly=(
            _withholding(
                month="2024-02",
                kind=WithholdingOperationKind.DAY_TRADE,
                gross="2.00",
                current="0.10",
                used="0.10",
                net="1.90",
            ),
        ),
        minimum_payment_monthly=(
            SimpleNamespace(
                competence_month="2024-01",
                payment_due_brl=Decimal("0.00"),
                closing_accumulated_tax_brl=Decimal("1.40"),
            ),
            SimpleNamespace(
                competence_month="2024-02",
                payment_due_brl=Decimal("0.00"),
                closing_accumulated_tax_brl=Decimal("7.60"),
            ),
        ),
        total_tax_due_brl=Decimal("8.00"),
        total_net_tax_due_brl=Decimal("7.60"),
        total_payment_due_brl=Decimal("0.00"),
        closing_accumulated_tax_brl=Decimal("7.60"),
        closing_common_withholding_balance_brl=Decimal("0.00"),
        closing_day_trade_withholding_balance_brl=Decimal("0.00"),
        closing_day_trade_loss_carryforward_brl=Decimal("25.00"),
    )

    contract = build_irpf_annual_assessment_contract(assessment)

    assert contract.schema_version == IRPF_ANNUAL_ASSESSMENT_SCHEMA_VERSION
    assert contract.portfolio_id == 7
    assert contract.year == 2024
    assert [item.competence_month for item in contract.monthly] == [
        "2024-01",
        "2024-02",
    ]
    assert contract.monthly[0].total_net_tax_due_brl == Decimal("1.40")
    assert contract.monthly[1].swing_net_tax_due_brl == Decimal("4.30")
    assert contract.monthly[1].day_trade_net_tax_due_brl == Decimal("1.90")
    assert contract.monthly[1].total_net_tax_due_brl == Decimal("6.20")
    assert contract.monthly[1].closing_accumulated_tax_brl == Decimal("7.60")
    assert contract.total_gross_tax_due_brl == Decimal("8.00")
    assert contract.total_withholding_brl == Decimal("0.40")
    assert contract.total_net_tax_due_brl == Decimal("7.60")
    assert contract.total_payment_due_brl == Decimal("0.00")
    assert contract.closing_accumulated_tax_brl == Decimal("7.60")
    assert contract.closing_day_trade_loss_carryforward_brl == Decimal("25.00")


def test_contract_to_dict_preserves_version_and_decimal_values() -> None:
    assessment = SimpleNamespace(
        portfolio_id=1,
        year=2025,
        swing=SimpleNamespace(monthly=()),
        common_withholding_monthly=(),
        day_trade_monthly=(),
        day_trade_withholding_monthly=(),
        minimum_payment_monthly=(),
        total_tax_due_brl=Decimal("0.00"),
        total_net_tax_due_brl=Decimal("0.00"),
        total_payment_due_brl=Decimal("0.00"),
        closing_accumulated_tax_brl=Decimal("0.00"),
        closing_common_withholding_balance_brl=Decimal("0.00"),
        closing_day_trade_withholding_balance_brl=Decimal("0.00"),
        closing_day_trade_loss_carryforward_brl=Decimal("0.00"),
    )

    payload = build_irpf_annual_assessment_contract(assessment).to_dict()

    assert payload["schema_version"] == "irpf-annual-assessment.v1"
    assert payload["monthly"] == ()
    assert payload["total_net_tax_due_brl"] == Decimal("0.00")
