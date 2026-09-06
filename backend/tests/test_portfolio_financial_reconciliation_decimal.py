from pathlib import Path


def test_independent_reconciliation_uses_decimal_without_float_arithmetic():
    source = Path("app/certification/portfolio_financial_reconciliation.py").read_text(
        encoding="utf-8"
    )

    assert "Decimal(" in source
    assert "float(" not in source
