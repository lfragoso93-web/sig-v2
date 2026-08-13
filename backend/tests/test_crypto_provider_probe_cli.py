from pathlib import Path


def test_crypto_provider_probe_is_read_only_and_requires_explicit_tickers() -> None:
    source = Path("app/cli/crypto_provider_probe.py").read_text(encoding="utf-8")

    assert "--ticker" in source
    assert "action=\"append\"" in source
    assert "if not tickers:" in source
    assert "fetch_brapi_crypto_history" in source
    assert "yf.Ticker" in source
    assert "AsyncSessionLocal" not in source
    assert "pg_insert" not in source
    assert "Asset.__table__.update" not in source
    assert "asset_prices" not in source
    assert "provider_status" not in source
