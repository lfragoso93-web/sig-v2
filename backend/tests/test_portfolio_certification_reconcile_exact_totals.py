from pathlib import Path


def test_reconciliation_cli_exposes_all_exact_total_fields():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    for field in (
        "remaining_cost=",
        "market_value=",
        "realized_pnl=",
        "open_pnl=",
        "income=",
        "total_pnl_with_income=",
    ):
        assert field in source
