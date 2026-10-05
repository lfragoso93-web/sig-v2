from decimal import Decimal
from pathlib import Path

from app.certification.portfolio_irpf_expectations import (
    EXPECTED_DISPOSALS_2026,
    EXPECTED_SYNTHETIC_IRPF_2026,
)


def test_synthetic_irpf_expectations_close_to_certified_fixture_disposals() -> None:
    expected = EXPECTED_SYNTHETIC_IRPF_2026

    assert expected.disposal_count == 2
    assert expected.total_common_gross_sales_brl == Decimal("3700.00")
    assert expected.total_swing_realized_pnl_brl == Decimal("450.80")
    assert expected.total_swing_taxable_base_brl == Decimal("198.00")
    assert expected.total_swing_tax_due_brl == Decimal("29.70")
    assert expected.common_withholding_brl == Decimal("0.19")
    assert expected.total_swing_net_tax_due_brl == Decimal("29.51")
    assert expected.total_payment_due_brl == Decimal("29.51")
    assert expected.total_day_trade_result_brl == Decimal("0.00")
    assert expected.total_day_trade_tax_due_brl == Decimal("0.00")

    assert EXPECTED_DISPOSALS_2026["CERT303-PETR4"]["realized_pnl_brl"] == Decimal(
        "252.80"
    )
    assert EXPECTED_DISPOSALS_2026["CERT303-PETR4"]["exemption_applied"] is True
    assert EXPECTED_DISPOSALS_2026["CERT303-BOVA11"]["realized_pnl_brl"] == Decimal(
        "198.00"
    )
    assert EXPECTED_DISPOSALS_2026["CERT303-BOVA11"]["exemption_applied"] is False


def test_synthetic_irpf_certification_cli_is_read_only_and_uses_canonical_pipeline() -> None:
    source = Path("app/cli/portfolio_irpf_certification.py").read_text(encoding="utf-8")

    for token in (
        "load_certification_portfolio_identity",
        "load_realized_disposals",
        "adapt_realized_disposals",
        "assess_annual_integrated_operations",
        "await db.rollback()",
        '"CERT303-IRPF"',
    ):
        assert token in source

    for forbidden in (
        "db.add(",
        "db.delete(",
        "db.commit(",
        "db.flush(",
        "insert(",
        "update(",
        "delete(",
    ):
        assert forbidden not in source
