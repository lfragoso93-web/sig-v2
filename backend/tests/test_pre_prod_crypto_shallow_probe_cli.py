from pathlib import Path


SOURCE = Path("app/cli/pre_prod_crypto_shallow_probe.py")


def test_shallow_probe_is_read_only_and_limited() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "pre_prod_crypto_shallow_history_audit" in source
    assert "period=\"max\"" in source
    assert "MAX_TICKERS_PER_PROBE = 20" in source
    assert '"yahoo_history_available"' in source
    assert '"yahoo_history_unavailable"' in source
    assert ".commit(" not in source
    assert "update(" not in source
    assert "insert(" not in source
    assert "_persist_result" not in source
