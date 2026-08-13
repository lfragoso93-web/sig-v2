from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import benchmark_rate_service
from app.services.corporate_action_engine import normalize_yahoo_splits
from app.services.corporate_event_service import sync_corporate_events_for_asset


@pytest.mark.asyncio
async def test_benchmark_import_repeated_execution_uses_upsert_without_duplicates(monkeypatch):
    rows = [
        {
            "indicator": "CDI",
            "date": date(2026, 8, 7),
            "source": "BCB_SGS",
            "value_field": "rate_daily",
            "value": "0.05",
        }
    ]
    fetcher = AsyncMock(return_value={"CDI": rows})
    monkeypatch.setattr(benchmark_rate_service, "fetch_many_sgs_series", fetcher)

    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    first = await benchmark_rate_service.import_benchmark_history(
        db,
        indicators=["CDI"],
        start_date=date(2026, 8, 7),
        end_date=date(2026, 8, 7),
    )
    second = await benchmark_rate_service.import_benchmark_history(
        db,
        indicators=["CDI"],
        start_date=date(2026, 8, 7),
        end_date=date(2026, 8, 7),
    )

    assert first == {"CDI": 1}
    assert second == {"CDI": 1}
    assert fetcher.await_count == 2
    assert db.commit.await_count == 2

    upserts = [
        call.args[0]
        for call in db.execute.await_args_list
        if "INSERT INTO rate_history" in str(call.args[0])
    ]
    assert len(upserts) == 2
    assert all("ON CONFLICT" in str(statement) for statement in upserts)


class _CorporateEventsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_corporate_event_sync_second_execution_does_not_create_duplicate(monkeypatch):
    asset = SimpleNamespace(
        id=7,
        ticker="TEST3",
        brapi_ticker=None,
        asset_type="ACAO",
    )
    brapi_fetcher = AsyncMock(return_value={"results": [{"symbol": "TEST3", "data": {}}]})
    yahoo_rows = [(date(2026, 1, 15), 2.0)]
    yahoo_fetcher = AsyncMock(return_value=yahoo_rows)
    expected_action = normalize_yahoo_splits("TEST3", yahoo_rows)[0]

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _CorporateEventsResult([]),
            _CorporateEventsResult(
                [(expected_action.source, expected_action.source_event_id, None)]
            ),
        ]
    )

    first = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )
    second = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=yahoo_fetcher,
    )

    assert len(first) == 1
    assert first[0].source_provider == "yahoo"
    assert first[0].source_event_id == expected_action.source_event_id
    assert second == []
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    assert brapi_fetcher.await_count == 2
    assert yahoo_fetcher.await_count == 2
