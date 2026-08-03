"""Testes da apuração mensal read-only de operações comuns."""

from datetime import date
from decimal import Decimal

from app.services.irpf_monthly_common_assessment import (
    assess_common_monthly_groups,
)
from app.services.irpf_realized_disposal_tax_adapter import (
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
) -> CanonicalRealizedDisposal:
    gross_value = Decimal(gross)
    cost_value = Decimal(cost)
    fees_value = Decimal(fees)
    return CanonicalRealizedDisposal(
        transaction_id=transaction_id,
        ticker=ticker,
        asset_type=asset_type,
        disposal_date=disposal_date,
        quantity_requested=Decimal(1),
        quantity_disposed=Decimal(1),
        unit_proceeds_brl=gross_value,
        gross_proceeds_brl=gross_value,
        cost_basis_brl=cost_value,
        fees_brl=fees_value,
        realized_pnl_brl=gross_value - cost_value - fees_value,
        currency="BRL",
        gross_proceeds_original_currency=None,
        applied_event_ids=(),
    )


def _assess(disposals: list[CanonicalRealizedDisposal]):
    groups = group_common_entries_by_month(adapt_realized_disposals(disposals))
    return assess_common_monthly_groups(groups)


def test_stock_sales_at_or_below_limit_are_exempt() -> None:
    assessments = _assess(
        [
            _disposal(
                transaction_id=1,
                ticker="VALE3",
                asset_type="ACAO",
                disposal_date=date(2024, 1, 10),
                gross="20000",
                cost="15000",
            )
        ]
    )

    item = assessments[0]
    assert item.group is TaxAssessmentGroup.STOCKS
    assert item.exemption_applied is True
    assert item.taxable_base_brl == Decimal("0.00")
    assert item.tax_due_brl == Decimal("0.00")


def test_stock_sales_above_limit_are_taxed_on_positive_pnl() -> None:
    item = _assess(
        [
            _disposal(
                transaction_id=1,
                ticker="PETR4",
                asset_type="ACAO",
                disposal_date=date(2024, 2, 10),
                gross="20000.01",
                cost="18000",
            )
        ]
    )[0]

    assert item.exemption_applied is False
    assert item.taxable_base_brl == Decimal("2000.01")
    assert item.tax_rate == Decimal("0.15")
    assert item.tax_due_brl == Decimal("300.00")


def test_bdr_does_not_receive_stock_monthly_exemption() -> None:
    item = _assess(
        [
            _disposal(
                transaction_id=1,
                ticker="AAPL34",
                asset_type="BDR",
                disposal_date=date(2024, 3, 10),
                gross="10000",
                cost="8000",
            )
        ]
    )[0]

    assert item.group is TaxAssessmentGroup.BDR
    assert item.exemption_limit_brl is None
    assert item.exemption_applied is False
    assert item.taxable_base_brl == Decimal("2000.00")
    assert item.tax_due_brl == Decimal("300.00")


def test_etf_and_real_estate_funds_keep_independent_rates() -> None:
    assessments = _assess(
        [
            _disposal(
                transaction_id=1,
                ticker="BOVA11",
                asset_type="ETF",
                disposal_date=date(2024, 4, 10),
                gross="10000",
                cost="9000",
            ),
            _disposal(
                transaction_id=2,
                ticker="MXRF11",
                asset_type="FII",
                disposal_date=date(2024, 4, 11),
                gross="10000",
                cost="9000",
            ),
        ]
    )

    assert [(item.group, item.tax_rate, item.tax_due_brl) for item in assessments] == [
        (TaxAssessmentGroup.ETF, Decimal("0.15"), Decimal("150.00")),
        (
            TaxAssessmentGroup.REAL_ESTATE_FUNDS,
            Decimal("0.20"),
            Decimal("200.00"),
        ),
    ]


def test_negative_result_does_not_generate_tax_without_loss_compensation() -> None:
    item = _assess(
        [
            _disposal(
                transaction_id=1,
                ticker="BOVA11",
                asset_type="ETF",
                disposal_date=date(2024, 5, 10),
                gross="9000",
                cost="10000",
            )
        ]
    )[0]

    assert item.realized_pnl_brl == Decimal("-1000.00")
    assert item.taxable_base_brl == Decimal("0.00")
    assert item.tax_due_brl == Decimal("0.00")


def test_tax_rounds_half_up_to_cents() -> None:
    item = _assess(
        [
            _disposal(
                transaction_id=1,
                ticker="BOVA11",
                asset_type="ETF",
                disposal_date=date(2024, 6, 10),
                gross="100.03",
                cost="100",
            )
        ]
    )[0]

    assert item.taxable_base_brl == Decimal("0.03")
    assert item.tax_due_brl == Decimal("0.00")
