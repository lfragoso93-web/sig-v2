from pathlib import Path


SOURCE = Path("app/cli/reconcile_crypto_gap_status.py")


def test_crypto_gap_reconcile_is_db_first_and_explicit_apply() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "pre_prod_crypto_seam_audit._run" in source
    assert "CRYPTO_TOP100_UNIVERSE_KEY" in source
    assert '"HISTORY_START_COMPLEMENT_GAPPED"' in source
    assert '"ACTIVE"' in source
    assert "--apply" in source
    assert "--all-crypto" in source
    assert "fetch_brapi" not in source
    assert "yfinance" not in source
