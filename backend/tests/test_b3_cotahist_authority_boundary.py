"""Protege a autoridade COTAHIST no baseline B3."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "app"
_B3_COTAHIST = _ROOT / "integrations" / "b3_cotahist.py"
_B3_CATALOG = _ROOT / "services" / "b3_cotahist_catalog_service.py"
_B3_REBUILD = _ROOT / "services" / "b3_historical_market_rebuild_service.py"
_ASSET_SEED = _ROOT / "services" / "asset_seed_service.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_cotahist_baseline_modules_do_not_import_lower_authority_providers() -> None:
    for path in (_B3_COTAHIST, _B3_CATALOG, _B3_REBUILD):
        source = _source(path)
        assert "yfinance" not in source
        assert "yahoo" not in source
        assert "app.integrations.brapi" not in source
        assert "fetch_all_tickers_v2" not in source


def test_brapi_asset_seed_cannot_create_missing_b3_assets() -> None:
    source = _source(_ASSET_SEED)

    assert "b3 é descoberta pelo cotahist" in source
    assert "async def _enrich_b3_asset" in source
    assert "if existing is none:\n        return \"skipped\"" in source
    assert "status = await _enrich_b3_asset" in source


def test_cotahist_rebuild_persists_official_ohlcv_not_close_only() -> None:
    source = _source(_B3_REBUILD)

    for field in ("open=record.open", "high=record.high", "low=record.low"):
        assert field in source
    assert "close=record.close" in source
    assert "volume=record.volume" in source
    assert 'source="b3_cotahist"' in source
