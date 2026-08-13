from pathlib import Path


SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "asset_price_global_backfill_service.py"
)


def _source() -> str:
    return SERVICE_PATH.read_text(encoding="utf-8")


def test_global_backfill_can_scope_candidates_to_crypto() -> None:
    source = _source()

    assert "asset_types: set[str] | None = None" in source
    assert "normalized_asset_types" in source
    assert "item.asset_type in normalized_asset_types" in source
    assert "scoped_coverage" in source


def test_global_backfill_can_scope_candidates_to_tickers() -> None:
    source = _source()

    assert "tickers: set[str] | None = None" in source
    assert "normalized_tickers" in source
    assert "item.ticker.upper() in normalized_tickers" in source


def test_crypto_scope_does_not_reopen_dedicated_price_types() -> None:
    source = _source()

    for token in (
        "AssetType.ACAO.value",
        "AssetType.FII.value",
        "AssetType.ETF_NACIONAL.value",
        "AssetType.BDR.value",
        "AssetType.TESOURO_DIRETO.value",
    ):
        assert token in source

    assert "item.asset_type not in _DEDICATED_BOOTSTRAP_PRICE_TYPES" in source
