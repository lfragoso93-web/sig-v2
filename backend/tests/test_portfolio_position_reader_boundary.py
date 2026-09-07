from pathlib import Path


def test_canonical_valuation_and_reconciliation_use_neutral_position_reader():
    valuation = Path("app/services/portfolio_canonical_valuation_service.py").read_text(
        encoding="utf-8"
    )
    reconcile = Path("app/cli/portfolio_certification_reconcile.py").read_text(
        encoding="utf-8"
    )

    expected_import = (
        "from app.services.portfolio_position_state_service import build_positions_at"
    )
    assert expected_import in valuation
    assert expected_import in reconcile
    assert "_build_positions_at" not in valuation
    assert "_build_positions_at" not in reconcile
