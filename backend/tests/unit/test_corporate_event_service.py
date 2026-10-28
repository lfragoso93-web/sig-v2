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
        isin_code="BRAERIACNOR0",
    )


@pytest.mark.asyncio
async def test_sync_persists_only_b3_events_for_listed_assets() -> None:
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
        raise AssertionError("Yahoo nao deve ser consultado para classe B3")

    async def b3_fetcher(ticker: str, asset_type: str):
        assert ticker == "AERI3" and asset_type == "ACAO"
        return {
            "code": "AERI", "stockDividends": [{
                "label": "BONIFICACAO", "factor": "5",
                "lastDatePrior": "03/01/2023", "isinCode": "BRAERIACNOR0",
            }], "subscriptions": [],
        }

    db = _db()
    created = await sync_corporate_events_for_asset(
        db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
        b3_fetcher=b3_fetcher,
    )

    assert len(created) == 1
    assert {event.event_type for event in created} == {"BONIFICACAO"}
    assert {event.ratio for event in created} == {Decimal("1.05")}
    assert all(event.ticker == "AERI3" for event in created)
    assert all(event.portfolio_id is None for event in created)
    assert all(event.source_provider == "b3" for event in created)
    assert all(event.record_date == date(2023, 3, 1) for event in created)
    assert all(event.effective_date is None for event in created)
    assert all("resolver data efetiva" in event.review_reason for event in created)
    assert all(event.source_event_id for event in created)
    assert all(event.source_payload_hash for event in created)
    assert all(event.raw_metadata is not None for event in created)
    assert all(event.brapi_event_id is None for event in created)
    assert all(event.raw_data is None for event in created)
    assert db.add.call_count == 1
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

    async def b3_fetcher(ticker: str, asset_type: str):
        return {
            "code": "AERI", "stockDividends": [{
                "label": "BONIFICACAO", "factor": "5",
                "lastDatePrior": "03/01/2023", "isinCode": "BRAERIACNOR0",
            }], "subscriptions": [],
        }

    first_db = _db()
    first = await sync_corporate_events_for_asset(
        first_db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
        b3_fetcher=b3_fetcher,
    )
    event = first[0]

    second_db = _db(existing=((event.source_provider, event.source_event_id),))
    second = await sync_corporate_events_for_asset(
        second_db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
        b3_fetcher=b3_fetcher,
    )

    assert second == []
    second_db.add.assert_not_called()
    second_db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_skips_crypto_without_provider_calls() -> None:
    brapi_fetcher = AsyncMock()
    yahoo_fetcher = AsyncMock()
    b3_fetcher = AsyncMock()
    db = _db()

    created = await sync_corporate_events_for_asset(
        db,
        _asset("CRIPTO"),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
        b3_fetcher=b3_fetcher,
    )

    assert created == []
    brapi_fetcher.assert_not_awaited()
    yahoo_fetcher.assert_not_awaited()
    b3_fetcher.assert_not_awaited()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_b3_corporate_actions_returns_none_for_unresolvable_ticker() -> None:
    from app.services.corporate_event_service import fetch_b3_corporate_actions

    result = await fetch_b3_corporate_actions("BRADESCO", "ACAO")
    assert result is None
