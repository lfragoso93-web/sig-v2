from pathlib import Path


SEED_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "asset_seed_service.py"
)


def test_asset_seed_uses_supported_crypto_universe_boundary() -> None:
    source = SEED_PATH.read_text(encoding="utf-8")

    assert (
        "from app.services.crypto_supported_universe_service import "
        "fetch_supported_crypto_universe"
    ) in source
    assert "coins = await fetch_supported_crypto_universe()" in source
    assert "fetch_crypto_catalog_all" not in source
    assert "fetch_crypto_available_all" not in source
