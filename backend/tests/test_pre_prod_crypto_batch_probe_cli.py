from pathlib import Path


CLI = Path("app/cli/pre_prod_crypto_batch_probe.py")


def test_crypto_batch_probe_composes_selection_and_read_only_probe() -> None:
    source = CLI.read_text(encoding="utf-8")

    assert "pre_prod_crypto_batch_selection" in source
    assert "crypto_provider_probe" in source
    assert "--limit" in source
    assert "--after-ticker" in source
    assert "brapi_and_yahoo" in source
    assert "brapi_only" in source
    assert "yahoo_only" in source
    assert "unavailable" in source
    assert "commit(" not in source
    assert "flush(" not in source
    assert "pg_insert" not in source
    assert "Asset.__table__.update" not in source
