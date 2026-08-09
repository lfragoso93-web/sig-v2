from pathlib import Path


SEED_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "asset_seed_service.py"
)


def test_asset_seed_uses_safe_crypto_catalog_adapter() -> None:
    source = SEED_PATH.read_text(encoding="utf-8")

    assert "from app.integrations.brapi_crypto_catalog import fetch_crypto_catalog_all" in source
    assert "coins = await fetch_crypto_catalog_all()" in source
    assert "fetch_crypto_available_all" not in source
