from pathlib import Path


def test_reconciliation_cli_validates_declared_expectations_before_db_comparison():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "assert_declared_financial_expectations" in source
    assert "assert_declared_financial_expectations(fixture, expected)" in source
