import pytest

from app.services.asset_enrichment_service import AssetEnrichmentService


@pytest.mark.asyncio
async def test_cached_asset_enrichment_reads_persisted_cache_without_provider_calls(monkeypatch):
    service = AssetEnrichmentService()
    reads = []

    async def cached(key):
        reads.append(key)
        return {"symbol": "PETR4", "pe": 5.2, "pb": 1.1, "roe": 0.2} if key == "stock_fundamentals:PETR4" else None

    async def coverage(_ticker):
        return None

    monkeypatch.setattr(service, "_get_cached", cached)
    monkeypatch.setattr("app.services.asset_enrichment_service.asset_coverage_service.get_coverage", coverage)
    result = await service.get_cached_asset_enrichment("petr4", "ACAO")

    assert result["ticker"] == "PETR4"
    assert result["coverage_status"] == "UNKNOWN"
    assert result["stock_fundamentals"]["pe"] == 5.2
    assert reads == ["dividend_history:v2:PETR4", "intl_fundamentals:PETR4", "stock_fundamentals:PETR4"]


@pytest.mark.asyncio
async def test_cached_fii_comparison_does_not_fall_back_to_provider(monkeypatch):
    service = AssetEnrichmentService()
    reads = []

    async def cached(key):
        reads.append(key)
        return {"pvp": 0.9, "physical_vacancy": 0.03} if key == "fii_indicators:HGLG11" else None

    async def coverage(_ticker):
        return None

    monkeypatch.setattr(service, "_get_cached", cached)
    monkeypatch.setattr("app.services.asset_enrichment_service.asset_coverage_service.get_coverage", coverage)
    result = await service.get_cached_asset_enrichment("HGLG11", "FII")

    assert result["fii_indicators"] == {"pvp": 0.9, "physical_vacancy": 0.03}
    assert reads == ["dividend_history:v2:HGLG11", "fii_indicators:HGLG11"]
