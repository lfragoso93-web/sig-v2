from pathlib import Path


def test_reconciliation_cli_uses_fixture_market_date_as_target():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert 'date.fromisoformat(fixture["market_prices"]["as_of"])' in source
