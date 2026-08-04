"""Testes do adaptador fiscal read-only para baixas canônicas."""

from datetime import date
from decimal import Decimal

import pytest
from app.services.irpf_realized_disposal_tax_adapter import (
    adapt_realized_disposal,
    adapt_realized_disposals,
    group_common_entries_by_month,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup
from app.services.position_timeline_projection import CanonicalRealizedDisposal


def _disposal(
    *,
    transaction_id: int,
    ticker: str,
    asset_type: str,
    disposal_date: date,
    gross: str,
    cost: str,
    fees: str = "0",
    quantity_requested: str = "10",
    quantity_disposed: str = "10",
) -> CanonicalRealizedDisposal:
    gross_value = Decimal(gross)
    cost_value = Decimal(cost)
    fees_value = Decimal(fees)
    return CanonicalRealizedDisposal(
        transaction_id=transaction_id,
        ticker=ticker,
        asset_type=asset_type,
        disposal_date=disposal_date,
        quantity_requested=Decimal(quantity_requested),
        quantity_disposed=Decimal(quantity_disposed),
        unit_proceeds_brl=gross_value / Decimal(quantity_disposed),
        gross_proceeds_brl=gross_value,
        cost_basis_brl=cost_value,
        fees_brl=fees_value,
        realized_pnl_brl=gross_value - cost_value - fees_value,
        currency="BRL",
        gross_proceeds_original_currency=None,
        applied_event_ids=(),
    )


def test_adapter_preserves_canonical_financial_values() -> None:
    disposal = _disposal(
        transaction_id=1,
        ticker="BOVA11",
        asset_type="ETF",
        disposal_date=date(2024, 2, 15),
        gross="120",
        cost="100",
        fees="3",
        quantity_requested="15",
        quantity_disposed="10",
    )

    entry = adapt_realized_disposal(disposal)

    assert entry.competence_month == "2024-02"
    assert entry.quantity_requested == Decimal(15)
    assert entry.quantity_disposed == Decimal(10)
    assert entry.gross_proceeds_brl == Decimal(120)
    assert entry.cost_basis_brl == Decimal(100)
    assert entry.fees_brl == Decimal(3)
    assert entry.realized_pnl_brl == Decimal(17)
    assert entry.common_group is TaxAssessmentGroup.ETF


def test_bdr_is_adapted_as_taxable_group_without_stock_exemption() -> None:
    entry = adapt_realized_disposal(
        _disposal(
            transaction_id=2,
            ticker="AAPL34",
            asset_type="BDR",
            disposal_date=date(2024, 3, 10),
            gross="15000",
            cost="10000",
        )
    )

    assert entry.asset_type == "BDR"
    assert entry.common_group is TaxAssessmentGroup.BDR
    assert entry.policy.common_rate == Decimal("0.15")
    assert entry.policy.monthly_exemption_limit is None


def test_fii_uses_twenty_percent_common_policy() -> None:
    entry = adapt_realized_disposal(
        _disposal(
            transaction_id=3,
            ticker="MXRF11",
            asset_type="FII",
            disposal_date=date(2024, 4, 10),
            gross="1200",
            cost="1000",
        )
    )

    assert entry.common_group is TaxAssessmentGroup.REAL_ESTATE_FUNDS
    assert entry.policy.common_rate == Decimal("0.20")
    assert entry.policy.monthly_exemption_limit is None


def test_monthly_grouping_does_not_mix_tax_classes() -> None:
    entries = adapt_realized_disposals(
        [
            _disposal(
                transaction_id=1,
                ticker="VALE3",
                asset_type="ACAO",
                disposal_date=date(2024, 5, 2),
                gross="6000",
                cost="5000",
            ),
            _disposal(
                transaction_id=2,
                ticker="AAPL34",
                asset_type="BDR",
                disposal_date=date(2024, 5, 3),
                gross="9000",
                cost="7000",
            ),
            _disposal(
                transaction_id=3,
                ticker="BOVA11",
                asset_type="ETF",
                disposal_date=date(2024, 5, 4),
                gross="8000",
                cost="7500",
            ),
            _disposal(
                transaction_id=4,
                ticker="MXRF11",
                asset_type="FII",
                disposal_date=date(2024, 5, 5),
                gross="4000",
                cost="3500",
            ),
        ]
    )

    groups = group_common_entries_by_month(entries)

    assert [(group.competence_month, group.group) for group in groups] == [
        ("2024-05", TaxAssessmentGroup.BDR),
        ("2024-05", TaxAssessmentGroup.ETF),
        ("2024-05", TaxAssessmentGroup.REAL_ESTATE_FUNDS),
        ("2024-05", TaxAssessmentGroup.STOCKS),
    ]
    assert [group.realized_pnl_brl for group in groups] == [
        Decimal(2000),
        Decimal(500),
        Decimal(500),
        Decimal(1000),
    ]


def test_monthly_grouping_keeps_months_independent() -> None:
    groups = group_common_entries_by_month(
        adapt_realized_disposals(
            [
                _disposal(
                    transaction_id=1,
                    ticker="BOVA11",
                    asset_type="ETF",
                    disposal_date=date(2024, 6, 30),
                    gross="1000",
                    cost="800",
                ),
                _disposal(
                    transaction_id=2,
                    ticker="BOVA11",
                    asset_type="ETF",
                    disposal_date=date(2024, 7, 1),
                    gross="1100",
                    cost="900",
                ),
            ]
        )
    )

    assert [group.competence_month for group in groups] == ["2024-06", "2024-07"]
    assert [group.realized_pnl_brl for group in groups] == [
        Decimal(200),
        Decimal(200),
    ]


def test_unknown_class_is_rejected_without_fiscal_fallback() -> None:
    with pytest.raises(ValueError, match="classe fiscal não suportada"):
        adapt_realized_disposal(
            _disposal(
                transaction_id=4,
                ticker="UNKNOWN",
                asset_type="OUTRO",
                disposal_date=date(2024, 5, 10),
                gross="100",
                cost="90",
            )
        )
