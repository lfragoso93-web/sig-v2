from pathlib import Path


def test_reconciliation_cli_compares_price_pnl_plus_income_to_independent_total():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert 'total_pnl_with_income = _money(totals["total_pnl"]) + income' in source
    assert "total_pnl_with_income != expected.total_pnl" in source
