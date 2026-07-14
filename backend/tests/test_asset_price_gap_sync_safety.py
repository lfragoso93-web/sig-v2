from app.models.asset import AssetType
from app.services.asset_price_gap_sync_service import (
    MAX_REASONABLE_UNIT_PRICE,
    _is_valid_price,
    normalize_provider_symbol,
)


def test_rejects_non_finite_and_absurd_prices() -> None:
    assert _is_valid_price(None) is False
    assert _is_valid_price(0) is False
    assert _is_valid_price(-1) is False
    assert _is_valid_price(float("nan")) is False
    assert _is_valid_price(float("inf")) is False
    assert _is_valid_price(MAX_REASONABLE_UNIT_PRICE) is False
    assert _is_valid_price(10_033_848_320.0) is False


def test_accepts_normal_unit_price() -> None:
    assert _is_valid_price(123.45678901) is True


def test_fractional_market_uses_base_provider_symbol() -> None:
    assert normalize_provider_symbol("WEGE3F", AssetType.ACAO) == "WEGE3"
    assert normalize_provider_symbol("TAEE11F", AssetType.ACAO) == "TAEE11"
    assert normalize_provider_symbol("XPML11", AssetType.FII) == "XPML11"


def test_international_symbol_is_not_rewritten() -> None:
    assert normalize_provider_symbol("NVDA", AssetType.STOCK) == "NVDA"
