from pathlib import Path


SOURCE = Path("app/cli/pre_prod_crypto_readiness_audit.py")


def test_crypto_readiness_audit_is_read_only_and_fail_closed() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "pre_prod_crypto_seam_audit" in source
    assert "pre_prod_crypto_shallow_history_audit" in source
    assert "HISTORY_START_TRUNCATED" in source
    assert "HISTORY_START_COMPLEMENT_GAPPED" in source
    assert "HISTORY_START_SHALLOW" in source
    assert "HISTORY_START_SHALLOW_VERIFIED" not in source
    assert '"crypto_price_history_ready"' in source
    assert '"no_history"' in source
    assert '"duplicates"' in source
    assert '"shallow_histories"' in source
    assert "and shallow_histories == 0" in source
    assert "fetch_brapi" not in source
    assert "yfinance" not in source
    assert ".commit(" not in source
    assert "update(" not in source
    assert "insert(" not in source
