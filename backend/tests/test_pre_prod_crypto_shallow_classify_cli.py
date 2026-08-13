from pathlib import Path


SOURCE = Path("app/cli/pre_prod_crypto_shallow_classify.py")


def test_shallow_classify_is_read_only_and_explicit() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "pre_prod_crypto_shallow_probe" in source
    assert '"recoverable_shallow"' in source
    assert '"legitimate_shallow"' in source
    assert "yahoo_first < brapi_first" in source
    assert "MAX_TICKERS_PER_CLASSIFY = 20" in source
    assert ".commit(" not in source
    assert "update(" not in source
    assert "insert(" not in source
    assert "_persist_result" not in source
