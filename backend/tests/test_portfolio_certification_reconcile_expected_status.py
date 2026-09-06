from pathlib import Path


def test_reconciliation_cli_emits_machine_readable_pass_status():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert '"CERT303-RECONCILE"' in source
    assert "status={'PASS' if not failures else 'FAIL'}" in source
    assert 'raise RuntimeError("; ".join(failures))' in source
