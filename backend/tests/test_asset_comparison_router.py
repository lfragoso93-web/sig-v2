from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.routers.assets import AssetComparisonRequest, compare_assets


@pytest.mark.asyncio
async def test_comparison_requires_two_to_six_distinct_catalog_assets():
    db = AsyncMock()

    with pytest.raises(HTTPException) as too_few:
        await compare_assets(AssetComparisonRequest(asset_ids=[1]), db, None)
    assert too_few.value.status_code == 422
    db.execute.assert_not_awaited()

    with pytest.raises(HTTPException) as duplicate:
        await compare_assets(AssetComparisonRequest(asset_ids=[1, 1]), db, None)
    assert duplicate.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_comparison_requires_every_asset_to_exist_in_catalog():
    db = AsyncMock()
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as missing:
        await compare_assets(AssetComparisonRequest(asset_ids=[1, 2]), db, None)

    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_comparison_returns_catalog_order_and_cached_enrichment(monkeypatch):
    assets = [
        SimpleNamespace(id=2, ticker="VALE3", name="Vale", asset_type="ACAO", currency="BRL", last_price=61.2, last_price_updated_at=None),
        SimpleNamespace(id=1, ticker="PETR4", name="Petrobras", asset_type="ACAO", currency="BRL", last_price=None, last_price_updated_at=None),
    ]
    db = AsyncMock()
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: assets))
    db.execute = AsyncMock(return_value=result)

    from app.services.asset_enrichment_service import asset_enrichment_service

    cached_reader = AsyncMock(side_effect=lambda ticker, asset_type: {
        "ticker": ticker,
        "asset_class": asset_type,
        "coverage_status": "UNKNOWN",
        "stock_fundamentals": None,
    })
    monkeypatch.setattr(asset_enrichment_service, "get_cached_asset_enrichment", cached_reader)

    response = await compare_assets(AssetComparisonRequest(asset_ids=[1, 2]), db, None)

    assert [item.ticker for item in response] == ["PETR4", "VALE3"]
    assert response[0].last_price is None
    assert response[1].last_price == 61.2
    assert cached_reader.await_count == 2
