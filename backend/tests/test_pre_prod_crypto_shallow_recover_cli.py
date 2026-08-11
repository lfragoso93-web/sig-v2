from pathlib import Path


SOURCE = Path("app/cli/pre_prod_crypto_shallow_recover.py")


def test_shallow_recover_is_explicit_limited_and_preserves_brapi() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "pre_prod_crypto_shallow_classify" in source
    assert "MAX_TICKERS_PER_RECOVERY = 20" in source
    assert 'parser.add_argument("--apply", action="store_true")' in source
    assert '"recoverable_shallow"' in source
    assert "timestamp.date() < brapi_first" in source
    assert "_convert_crypto_usd_rows_to_brl" in source
    assert "_persist_result" in source
    assert '"yfinance_crypto_ptax_brl_max"' in source
    assert '"HISTORY_START_SHALLOW_VERIFIED"' in source
    assert '"HISTORY_START_SHALLOW_UNAVAILABLE"' in source
    assert '"HISTORY_START_COMPLEMENT_GAPPED"' in source
    assert '"HISTORY_START_COMPLEMENT_UNAVAILABLE"' in source
