from pathlib import Path


def test_independent_reconciliation_does_not_import_financial_services_or_models():
    source = Path("app/certification/portfolio_financial_reconciliation.py").read_text(
        encoding="utf-8"
    )

    assert "app.services" not in source
    assert "app.models" not in source
    assert "sqlalchemy" not in source
    assert "AsyncSession" not in source
