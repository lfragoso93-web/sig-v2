from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "app" / "integrations" / "brapi_crypto_history.py"
GAP_SYNC = ROOT / "app" / "services" / "asset_price_gap_sync_service.py"


def test_brapi_crypto_adapter_is_isolated_and_historical() -> None:
    source = ADAPTER.read_text(encoding="utf-8")

    assert '_BRAPI_CRYPTO_URL = "https://brapi.dev/api/v2/crypto"' in source
    assert '"range": range_' in source
    assert '"interval": interval' in source
    assert '"currency": currency.upper()' in source
    assert "fetch_brapi_crypto_history" in source


def test_crypto_gap_sync_prefers_brapi_and_keeps_yahoo_fallback() -> None:
    source = GAP_SYNC.read_text(encoding="utf-8")

    assert "from app.integrations.brapi_crypto_history import fetch_brapi_crypto_history" in source
    assert "rows = await fetch_brapi_crypto_history(" in source
    assert 'return rows, "brapi_v2_crypto_max", "brapi"' in source
    assert 'return fallback, "yfinance_crypto_max", "yfinance"' in source
    assert source.index("fetch_brapi_crypto_history") < source.index("fallback = await _fetch_yf_max")
