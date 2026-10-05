from pathlib import Path


def test_reconciliation_cli_does_not_import_provider_integrations():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "app.integrations" not in source
    assert "brapi" not in source.lower()
    assert "bcb" not in source.lower()
