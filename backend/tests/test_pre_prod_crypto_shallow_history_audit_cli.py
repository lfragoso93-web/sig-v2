from pathlib import Path


SOURCE = Path("app/cli/pre_prod_crypto_shallow_history_audit.py")


def test_crypto_shallow_history_audit_is_db_only_and_read_only() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "SHALLOW_MAX_ROWS" in source
    assert "SHALLOW_MAX_AGE_DAYS" in source
    assert '"shallow_histories"' in source
    assert "AssetPrice" in source
    assert "fetch_brapi" not in source
    assert "yfinance" not in source
    assert ".commit(" not in source
    assert "update(" not in source
    assert "insert(" not in source
