from pathlib import Path


def test_reconciliation_cli_reads_income_from_canonical_dividend_service():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "from app.services.dividend_service import" in source
    assert "list_dividends" in source
    assert "PortfolioAccessContext.for_user" in source
    assert "await list_dividends(db, access)" in source
    assert "item.total_received" in source
