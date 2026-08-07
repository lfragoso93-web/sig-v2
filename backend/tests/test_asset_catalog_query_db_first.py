from pathlib import Path

from app.models.asset import AssetType
from app.services.asset_catalog_query_service import _normalize_filter


SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "asset_catalog_query_service.py"
)


def test_catalog_aliases_map_to_persisted_asset_types() -> None:
    assert _normalize_filter("cripto") == (AssetType.CRIPTO.value,)
    assert _normalize_filter("stock_int") == (AssetType.STOCK.value,)
    assert _normalize_filter("etf_int") == (AssetType.ETF_INTERNACIONAL.value,)
    assert _normalize_filter("tesouro") == (AssetType.TESOURO_DIRETO.value,)


def test_catalog_query_service_has_no_provider_dependencies() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    forbidden = {
        "app.integrations",
        "yfinance",
        "fetch_ticker_suggestions",
        "fetch_crypto_suggestions",
        "fetch_treasury_list",
        "fetch_asset_info",
    }
    findings = sorted(token for token in forbidden if token in source)
    assert findings == []


def test_catalog_query_is_read_only() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    forbidden = {"commit()", "flush()", "add(", "delete(", "update("}
    findings = sorted(token for token in forbidden if token in source)
    assert findings == []
