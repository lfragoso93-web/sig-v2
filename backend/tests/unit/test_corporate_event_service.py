from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.corporate_event_service import sync_corporate_events_for_asset


def _result(values):
    result = Mock()
    result.all.return_value = values
    return result


def _db(existing=()):
    return SimpleNamespace(
        execute=AsyncMock(return_value=_result(existing)),
        add=Mock(),
        flush=AsyncMock(),
    )


def _asset(asset_type="ACAO"):
    return SimpleNamespace(
        id=7,
        ticker="AERI3",
        brapi_ticker=None,
        asset_type=asset_type,
    )


@pytest.mark.asyncio
async def test_sync_persists_global_brapi_and_yahoo_events() -> None:
    async def brapi_fetcher(ticker: str):
        assert ticker == "AERI3"
        return {
            "results": [{
                "symbol": "AERI3",
                "data": {
                    "stockDividends": [{
                        "factor": 1.05,
                        "lastDatePrior": "2023-03-01",
                    }],
                    "subscriptions": [],
                },
            }],
        }

    async def yahoo_fetcher(symbol: str):
        assert symbol == "AERI3.SA"
        return [(date(2024, 5, 14), 0.05)]

    db = _db()
    created = await sync_corporate_events_for_asset(
        db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )

    assert len(created) == 2
    assert {event.event_type for event in created} == {"BONIFICACAO", "GRUPAMENTO"}
    assert {event.ratio for event in created} == {Decimal("1.05"), Decimal("0.05")}
    assert all(event.ticker == "AERI3" for event in created)
    assert all(event.portfolio_id is None for event in created)
    assert all(event.source_provider in {"brapi", "yahoo"} for event in created)
    assert all(event.source_event_id for event in created)
    assert all(event.source_payload_hash for event in created)
    assert all(event.raw_metadata is not None for event in created)
    assert all(event.brapi_event_id is None for event in created)
    assert all(event.raw_data is None for event in created)
    assert db.add.call_count == 2
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_is_idempotent_by_canonical_source_event_id() -> None:
    payload = {
        "results": [{
            "symbol": "AERI3",
            "data": {
                "stockDividends": [{
                    "factor": 1.05,
                    "lastDatePrior": "2023-03-01",
                }],
            },
        }],
    }

    async def brapi_fetcher(ticker: str):
        return payload

    async def yahoo_fetcher(symbol: str):
        return []

    first_db = _db()
    first = await sync_corporate_events_for_asset(
        first_db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )
    event = first[0]

    second_db = _db(existing=((event.source_provider, event.source_event_id),))
    second = await sync_corporate_events_for_asset(
        second_db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )

    assert second == []
    second_db.add.assert_not_called()
    second_db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_skips_unsupported_asset_class_without_provider_calls() -> None:
    brapi_fetcher = AsyncMock()
    yahoo_fetcher = AsyncMock()
    db = _db()

    created = await sync_corporate_events_for_asset(
        db,
        _asset("FII"),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )

    assert created == []
    brapi_fetcher.assert_not_awaited()
    yahoo_fetcher.assert_not_awaited()
    db.execute.assert_not_awaited()
