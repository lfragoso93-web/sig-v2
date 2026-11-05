from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.routers.assets import AssetComparisonRequest, compare_assets, get_asset_analysis


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


@pytest.mark.asyncio
async def test_asset_analysis_reads_catalog_history_and_cached_fields(monkeypatch):
    from datetime import date, datetime, timezone

    from app.services.asset_enrichment_service import asset_enrichment_service

    asset = SimpleNamespace(
        id=7, ticker="PETR4", name="Petrobras", asset_type="ACAO", currency="BRL",
        sector="Energy", sub_sector="Oil", isin_code="BRPETRACNPR6", provider="brapi",
        provider_status="active", provider_last_sync_at=None, last_price=37.5,
        last_price_updated_at=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=asset)
    price = SimpleNamespace(
        timestamp=datetime(2026, 11, 3, tzinfo=timezone.utc), open=36, high=38,
        low=35, close=37.5, volume=1000, source="b3",
    )
    dividend = SimpleNamespace(
        record_date=None, ex_date=date(2026, 10, 1), payment_date=None,
        dividend_type="DIVIDENDO", value_per_unit=0.5, source="b3", remarks=None,
    )
    event = SimpleNamespace(
        event_type="DESDOBRAMENTO", status="PENDENTE", reconciliation_status="UNRECONCILED",
        requires_review=True, effective_date=None, announcement_date=None,
        description="Evento pendente", source_provider="b3",
    )
    results = [price, dividend, event]
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [results[0]])),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [results[1]])),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [results[2]])),
    ])
    cached_reader = AsyncMock(return_value={"ticker": "PETR4", "coverage_status": "PARTIAL", "stock_fundamentals": {"pe": 5}})
    monkeypatch.setattr(asset_enrichment_service, "get_cached_asset_enrichment", cached_reader)

    response = await get_asset_analysis(7, db, None)

    assert response["asset"]["ticker"] == "PETR4"
    assert response["enrichment"]["stock_fundamentals"]["pe"] == 5
    assert response["price_history"][0]["close"] == 37.5
    assert response["dividends"][0]["value_per_unit"] == 0.5
    assert response["corporate_events"][0]["requires_review"] is True
    assert response["reports"] == []
    event_query = db.execute.await_args_list[2].args[0]
    assert "corporate_events.portfolio_id IS NULL" in str(event_query)
    cached_reader.assert_awaited_once_with("PETR4", "ACAO")


@pytest.mark.asyncio
async def test_asset_analysis_requires_catalog_asset():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as missing:
        await get_asset_analysis(99, db, None)
    assert missing.value.status_code == 404
@pytest.mark.asyncio
async def test_asset_analysis_resolves_by_ticker_symbol(monkeypatch):
    from app.services.asset_enrichment_service import asset_enrichment_service

    asset = SimpleNamespace(
        id=14, ticker="VALE3", name="Vale", asset_type="ACAO", currency="BRL",
        sector="Materials", sub_sector="Mining", isin_code="BRVALEACNOR0", provider="brapi",
        provider_status="active", provider_last_sync_at=None, last_price=65.0,
        last_price_updated_at=None,
    )
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: asset)),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])),
    ])
    cached_reader = AsyncMock(return_value={"ticker": "VALE3", "coverage_status": "FULL"})
    monkeypatch.setattr(asset_enrichment_service, "get_cached_asset_enrichment", cached_reader)

    response = await get_asset_analysis("vale3", db, None)
    assert response["asset"]["id"] == 14
    assert response["asset"]["ticker"] == "VALE3"
