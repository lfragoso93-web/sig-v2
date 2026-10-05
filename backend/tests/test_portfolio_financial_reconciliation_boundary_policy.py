from pathlib import Path


def test_independent_reconciliation_does_not_import_seed_implementation():
    source = Path("app/certification/portfolio_financial_reconciliation.py").read_text(
        encoding="utf-8"
    )

    assert "portfolio_seed_asset_policy" not in source
    assert "portfolio_seed_transaction_service" not in source
    assert "portfolio_seed_market_price_service" not in source
    assert "portfolio_seed_treasury_price_service" not in source
    assert "portfolio_seed_benchmark_rate_service" not in source
