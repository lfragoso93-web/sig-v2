from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_crypto_financial_certification_reconcile_is_db_first_and_fail_closed():
    source = (
        ROOT / "app" / "cli" / "reconcile_crypto_financial_certification.py"
    ).read_text(encoding="utf-8")

    assert "pre_prod_crypto_readiness_audit._run()" in source
    assert "CRYPTO_TOP100_UNIVERSE_KEY" in source
    assert "seam_status\"] == \"continuous\"" in source
    assert "\"HISTORY_START_EXHAUSTED\"" in source
    assert "httpx" not in source
    assert "yfinance" not in source
