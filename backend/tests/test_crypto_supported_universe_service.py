import pytest
from app.services import crypto_supported_universe_service as service


@pytest.mark.asyncio
async def test_supported_universe_is_top_market_cap_intersection_with_brapi(monkeypatch) -> None:
    async def fake_ranking(limit: int = 100):
        assert limit == 100
        return [
            {"symbol": "BTC", "name": "Bitcoin", "market_cap_rank": 1, "market_cap": 10, "source_id": "bitcoin"},
            {"symbol": "ETH", "name": "Ethereum", "market_cap_rank": 2, "market_cap": 9, "source_id": "ethereum"},
            {"symbol": "NOPE", "name": "Unsupported", "market_cap_rank": 3, "market_cap": 8, "source_id": "nope"},
        ]

    async def fake_catalog():
        return [{"coin": "ETH"}, {"coin": "BTC"}, {"coin": "DOGE"}]

    monkeypatch.setattr(service, "fetch_top_crypto_by_market_cap", fake_ranking)
    monkeypatch.setattr(service, "fetch_crypto_catalog_all", fake_catalog)

    result = await service.fetch_supported_crypto_universe()

    assert [item.ticker for item in result] == ["BTC", "ETH"]
    assert [item.market_cap_rank for item in result] == [1, 2]


@pytest.mark.asyncio
async def test_supported_universe_deduplicates_symbols(monkeypatch) -> None:
    async def fake_ranking(limit: int = 100):
        return [
            {"symbol": "AAA", "name": "First", "market_cap_rank": 1, "market_cap": 10, "source_id": "a"},
            {"symbol": "AAA", "name": "Second", "market_cap_rank": 2, "market_cap": 9, "source_id": "b"},
        ]

    async def fake_catalog():
        return [{"coin": "AAA"}]

    monkeypatch.setattr(service, "fetch_top_crypto_by_market_cap", fake_ranking)
    monkeypatch.setattr(service, "fetch_crypto_catalog_all", fake_catalog)

    result = await service.fetch_supported_crypto_universe()

    assert len(result) == 1
    assert result[0].market_cap_rank == 1
