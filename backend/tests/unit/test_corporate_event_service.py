import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.services.corporate_event_service import sync_corporate_events_for_asset


def _result(values):
    result = Mock()
    result.scalars.return_value.all.return_value = values
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
            "results": [
                {
                    "symbol": "AERI3",
                    "data": {
                        "stockDividends": [
                            {
                                "factor": 1.05,
                                "label": "BONIFICACAO",
                                "lastDatePrior": "2023-03-01",
                            }
                        ],
                        "subscriptions": [],
                    },
                }
            ],
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
    assert all(event.brapi_event_id for event in created)
    assert all(event.source_provider in {"brapi", "yahoo"} for event in created)
    assert all(event.source_event_id for event in created)
    assert all(event.source_payload_hash for event in created)
    assert all(event.economic_identity_hash for event in created)
    assert all(event.effective_date == event.event_date for event in created)
    assert all(event.quantity_factor == event.ratio for event in created)
    assert all(event.requires_review is True for event in created)
    assert all(event.reconciliation_status == "UNRECONCILED" for event in created)
    assert {json.loads(event.raw_data)["source"] for event in created} == {
        "brapi",
        "yahoo",
    }
    assert db.add.call_count == 2
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_is_idempotent_by_canonical_source_event_id() -> None:
    payload = {
        "results": [
            {
                "symbol": "AERI3",
                "data": {
                    "stockDividends": [
                        {
                            "factor": 1.05,
                            "label": "BONIFICACAO",
                            "lastDatePrior": "2023-03-01",
                        }
                    ],
                },
            }
        ],
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
    event_id = first[0].brapi_event_id

    second_db = _db(existing=(event_id,))
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
async def test_sync_persists_subscription_price_without_applying_quantity() -> None:
    async def brapi_fetcher(_ticker: str):
        return {
            "results": [
                {
                    "symbol": "AERI3",
                    "data": {
                        "subscriptions": [
                            {
                                "lastDatePrior": "2026-01-10",
                                "rate": "9.50",
                                "assetIssued": "BRAERIACNOR4",
                            }
                        ]
                    },
                }
            ]
        }

    async def yahoo_fetcher(_symbol: str):
        return []

    created = await sync_corporate_events_for_asset(
        _db(),
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )

    assert len(created) == 1
    assert created[0].event_type == "SUBSCRICAO"
    assert created[0].quantity_factor == Decimal(1)
    assert created[0].subscription_price == Decimal("9.50")


@pytest.mark.asyncio
async def test_sync_prefers_brapi_when_yahoo_has_equivalent_split() -> None:
    async def brapi_fetcher(_ticker: str):
        return {
            "results": [
                {
                    "symbol": "AERI3",
                    "data": {
                        "stockDividends": [
                            {
                                "factor": 2,
                                "label": "DESDOBRAMENTO",
                                "lastDatePrior": "2024-05-14",
                            }
                        ],
                    },
                }
            ],
        }

    async def yahoo_fetcher(_symbol: str):
        return [(date(2024, 5, 14), 2)]

    db = _db()
    created = await sync_corporate_events_for_asset(
        db,
        _asset(),
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )

    assert len(created) == 1
    assert created[0].event_type == "DESDOBRAMENTO"
    assert json.loads(created[0].raw_data)["source"] == "brapi"


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
