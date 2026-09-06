from pathlib import Path


def test_reconciliation_cli_does_not_provision_or_seed_state():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "provision_synthetic_user_portfolio" not in source
    assert "seed_transactions" not in source
    assert "seed_generic_market_prices" not in source
    assert "seed_synthetic" not in source
    assert "db.commit" not in source
    assert "db.add" not in source
