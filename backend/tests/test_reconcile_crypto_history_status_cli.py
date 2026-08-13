from pathlib import Path


CLI_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "reconcile_crypto_history_status.py"
)


def _source() -> str:
    return CLI_PATH.read_text(encoding="utf-8")


def test_reconciliation_is_explicit_and_db_only() -> None:
    source = _source()

    assert 'parser.add_argument("--apply", action="store_true")' in source
    assert 'parser.add_argument("--ticker", action="append", required=True)' in source
    assert "HISTORY_START_EXHAUSTED" in source
    assert "HISTORY_START_TRUNCATED" in source
    assert "fetch_brapi" not in source
    assert "yfinance" not in source


def test_reconciliation_requires_strict_canary_evidence() -> None:
    source = _source()

    for token in (
        'AssetType.CRIPTO.value',
        '"BRL"',
        '"brapi"',
        '"brapi_v2_crypto_max"',
        'EXPECTED_ROWS = 1000',
        'EXPECTED_FIRST_DATE = date(2023, 11, 15)',
        'EXPECTED_LAST_DATE = date(2026, 8, 10)',
        'EXPECTED_PROVIDER_ATTEMPTS = 2',
    ):
        assert token in source

    assert "provider_attempts" in source
    assert "provider_attempts_mismatch" in source
    assert "eligible" in source
