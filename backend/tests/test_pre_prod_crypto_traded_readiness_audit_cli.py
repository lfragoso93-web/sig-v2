from pathlib import Path

SOURCE = Path("app/cli/pre_prod_crypto_traded_readiness_audit.py")


def test_traded_crypto_readiness_audit_is_read_only_and_scoped() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "top_traded_crypto_transactions" in source
    assert "DEFAULT_LIMIT = 30" in source
    assert "pre_prod_crypto_seam_audit" in source
    assert "pre_prod_crypto_shallow_history_audit" in source
    assert "FINANCIALLY_CERTIFIED_CRYPTO_STATUSES" in source
    assert "fetch_brapi" not in source
    assert "yfinance" not in source
    assert ".commit(" not in source
    assert "update(" not in source
    assert "insert(" not in source
