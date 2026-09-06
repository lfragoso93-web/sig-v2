from pathlib import Path


def test_reconciliation_cli_checks_core_financial_dimensions():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    for token in (
        "quantity",
        "remaining-cost",
        "realized-pnl",
        '"remaining_cost"',
        '"market_value"',
        '"realized_pnl"',
        '"open_pnl"',
        "status={'PASS' if not failures else 'FAIL'}",
    ):
        assert token in source
