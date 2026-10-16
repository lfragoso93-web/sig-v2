from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cli import corporate_event_reconciliation_candidates as cli
from app.services.corporate_event_reconciliation_candidates import (
    discover_cross_provider_candidates,
)


def _event(
    event_id: int,
    *,
    source: str,
    ticker: str = "TEST3",
    event_type: str = "GRUPAMENTO",
    event_date: date = date(2026, 10, 13),
    factor: str = "0.2",
    status: str = "UNRECONCILED",
):
    return SimpleNamespace(
        id=event_id,
        ticker=ticker,
        event_type=event_type,
        source_provider=source,
        source_event_id=f"{source}:{event_id}",
        reconciliation_status=status,
        effective_date=event_date,
        event_date=event_date,
        quantity_factor=Decimal(factor),
        ratio=Decimal(factor),
    )


def test_discovers_exact_cross_provider_identity_only_as_review_candidate():
    candidates = discover_cross_provider_candidates(
        [
            _event(1, source="b3"),
            _event(2, source="yahoo", factor="0.2000"),
            _event(3, source="yahoo", factor="0.25"),
            _event(4, source="brapi", status="MATCHED"),
            _event(5, source="legacy"),
            _event(6, source="b3", ticker="OTHER3"),
        ]
    )

    assert len(candidates) == 1
    group = candidates[0]
    assert group.ticker == "TEST3"
    assert group.effective_date == date(2026, 10, 13)
    assert group.quantity_factor == Decimal("0.2")
    assert [event.event_id for event in group.events] == [1, 2]
    assert group.review_required is True
    assert group.automatic_match_allowed is False


def test_does_not_candidate_group_from_single_provider_duplicates():
    candidates = discover_cross_provider_candidates(
        [_event(1, source="yahoo"), _event(2, source="yahoo")]
    )

    assert candidates == ()


@pytest.mark.asyncio
async def test_candidates_cli_report_is_read_only(monkeypatch):
    groups = discover_cross_provider_candidates(
        [_event(10, source="b3"), _event(11, source="yahoo")]
    )
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=object())
    session.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(
        cli,
        "load_cross_provider_candidates",
        AsyncMock(return_value=groups),
    )

    report = await cli._main("TEST3")

    assert report["schema_version"] == "corporate-event-reconciliation-candidates.v1"
    assert report["read_only"] is True
    assert report["database_writes_executed"] == 0
    assert report["automatic_match_allowed"] is False
    assert report["candidate_group_count"] == 1
    assert [item["event_id"] for item in report["candidate_groups"][0]["events"]] == [10, 11]
