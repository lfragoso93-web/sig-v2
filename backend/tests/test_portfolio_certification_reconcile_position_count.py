from pathlib import Path


def test_reconciliation_cli_rejects_missing_and_unexpected_positions():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "missing-position" in source
    assert "unexpected-positions=" in source
