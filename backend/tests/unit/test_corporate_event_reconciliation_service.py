from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.models.corporate_event import CorporateEvent
from app.services.corporate_event_reconciliation_service import (
    reconcile_corporate_event_records,
    reconcile_corporate_events_for_asset,
)

NOW = datetime(2026, 7, 31, 18, 0, tzinfo=UTC)


def _event(
    event_id: int,
    *,
    source: str,
    factor: str = "2",
    event_type: str = "DESDOBRAMENTO",
) -> CorporateEvent:
    return CorporateEvent(
        id=event_id,
        asset_id=7,
        ticker="PETR4",
        event_type=event_type,
        status="DISCOVERED",
        reconciliation_status="UNRECONCILED",
        requires_review=True,
        source_provider=source,
        source_event_id=f"{source}:{event_id}",
        effective_date=date(2008, 4, 25),
        quantity_factor=Decimal(factor),
        currency="BRL",
        event_date=date(2008, 4, 25),
        ratio=Decimal(factor),
    )


def test_matching_sources_select_single_brapi_canonical_event() -> None:
    yahoo = _event(2, source="yahoo")
    brapi = _event(1, source="brapi")

    report = reconcile_corporate_event_records([yahoo, brapi], reconciled_at=NOW)

    assert report.total == 2
    assert report.matched == 2
    assert report.canonical == 1
    assert report.suppressed_equivalents == 1
    assert brapi.reconciliation_status == "MATCHED"
    assert brapi.is_canonical is True
    assert brapi.matched_event_id is None
    assert brapi.requires_review is False
    assert brapi.status == "VALIDATED"
    assert yahoo.reconciliation_status == "MATCHED"
    assert yahoo.is_canonical is False
    assert yahoo.matched_event_id == brapi.id
    assert yahoo.reconciled_at == NOW


def test_divergent_factors_are_marked_as_blocking_conflict() -> None:
    brapi = _event(1, source="brapi", factor="2")
    yahoo = _event(2, source="yahoo", factor="3")

    report = reconcile_corporate_event_records([brapi, yahoo], reconciled_at=NOW)

    assert report.conflicts == 2
    assert report.canonical == 0
    for event in (brapi, yahoo):
        assert event.reconciliation_status == "CONFLICT"
        assert event.is_canonical is False
        assert event.requires_review is True
        assert "divergem" in event.review_reason


def test_single_source_remains_unreconciled_and_requires_review() -> None:
    event = _event(1, source="brapi")

    report = reconcile_corporate_event_records([event], reconciled_at=NOW)

    assert report.unreconciled == 1
    assert report.canonical == 1
    assert event.reconciliation_status == "UNRECONCILED"
    assert event.is_canonical is True
    assert event.requires_review is True


def test_subscription_requires_review_even_when_sources_match() -> None:
    brapi = _event(1, source="brapi", factor="1", event_type="SUBSCRICAO")
    manual = _event(2, source="manual", factor="1", event_type="SUBSCRICAO")

    report = reconcile_corporate_event_records([brapi, manual], reconciled_at=NOW)

    assert report.matched == 2
    assert brapi.is_canonical is True
    assert brapi.requires_review is True
    assert brapi.status == "DISCOVERED"
    assert "exige revisão" in brapi.review_reason


async def test_persistent_reconciliation_flushes_without_committing() -> None:
    brapi = _event(1, source="brapi")
    yahoo = _event(2, source="yahoo")
    result = Mock()
    result.scalars.return_value.all.return_value = [brapi, yahoo]
    db = SimpleNamespace(
        flush=AsyncMock(),
        execute=AsyncMock(return_value=result),
        commit=AsyncMock(),
    )

    report = await reconcile_corporate_events_for_asset(db, asset_id=7)

    assert report.matched == 2
    assert db.flush.await_count == 2
    db.execute.assert_awaited_once()
    db.commit.assert_not_awaited()
