from pathlib import Path


def test_reconciliation_cli_uses_only_read_paths_after_identity_lookup():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "calculate_canonical_portfolio_totals" in source
    assert "_build_positions_at" in source
    assert "list_dividends" in source
    for forbidden in ("commit()", "flush()", "add(", "delete(", "update("):
        assert forbidden not in source
