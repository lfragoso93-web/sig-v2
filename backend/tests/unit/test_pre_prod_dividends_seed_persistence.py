from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.services.dividend_event_normalizer import ParsedDividendEvent
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAssetCollection,
    StrictDividendSourceCollection,
)
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedAlreadyRunningError,
    DividendsSeedPersistenceError,
    persist_asset_dividends_strict,
)


def _collection(
    *,
    value: float = 1.25,
    source: str = "brapi",
    record_date: date | None = date(2026, 7, 24),
    payment_date: date | None = date(2026, 8, 10),
    raw_payload: dict | None = None,
):
    event = ParsedDividendEvent(
        record_date=record_date,
        ex_date=date(2026, 7, 27),
        payment_date=payment_date,
        approved_on=None,
        value_per_unit=value,
        dividend_type="DIVIDENDO",
        raw_payload=raw_payload or {"rate": value},
    )
    return StrictDividendAssetCollection(
        ticker="PETR4",
        asset_type="ACAO",
        sources=(
            StrictDividendSourceCollection(
                source=source,
                raw_rows=1,
                normalized_rows=(event,),
                rejected_rows=0,
                empty_reason=None,
            ),
        ),
    )


def _result(rows):
    result = Mock()
    result.scalars.return_value.all.return_value = rows
    return result


def _db(*, acquired=True, assets=None, existing=None):
    return SimpleNamespace(
        scalar=AsyncMock(return_value=acquired),
        execute=AsyncMock(
            side_effect=[
                _result(assets or []),
                _result(existing or []),
            ]
        ),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        delete=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_creates_global_event_under_transaction_lock_without_commit() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    db = _db(assets=[asset])

    result = await persist_asset_dividends_strict(
        db=db,
        collections=(_collection(),),
    )

    assert result.created == 1
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.processed == 1
    db.add.assert_called_once()
    created = db.add.call_args.args[0]
    assert isinstance(created, AssetDividend)
    assert created.asset_id == 7
    assert created.dividend_type == DividendType.DIVIDENDO
    assert created.source == "brapi"
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_updates_existing_occurrence_metadata_when_identity_is_stable() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    existing = AssetDividend(
        asset_id=7,
        record_date=date(2026, 7, 24),
        ex_date=date(2026, 7, 27),
        payment_date=date(2026, 8, 10),
        value_per_unit=1.25,
        dividend_type=DividendType.DIVIDENDO,
        raw_payload={"rate": 1.25, "stale": True},
        source="brapi",
    )
    db = _db(assets=[asset], existing=[existing])

    result = await persist_asset_dividends_strict(
        db=db,
        collections=(_collection(value=1.25),),
    )

    assert result.updated == 1
    assert existing.value_per_unit == 1.25
    assert existing.raw_payload == {"rate": 1.25}
    db.add.assert_not_called()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_unchanged_event_does_not_flush() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    event = _collection().sources[0].normalized_rows[0]
    existing = AssetDividend(
        asset_id=7,
        ex_date=event.ex_date,
        dividend_type=DividendType.DIVIDENDO,
        record_date=event.record_date,
        payment_date=event.payment_date,
        approved_on=event.approved_on,
        value_per_unit=1.25,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
        raw_payload={"rate": 1.25},
        source="brapi",
    )
    db = _db(assets=[asset], existing=[existing])

    result = await persist_asset_dividends_strict(db=db, collections=(_collection(),))

    assert result.unchanged == 1
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_missing_catalog_asset_without_creating_it() -> None:
    db = _db()

    with pytest.raises(DividendsSeedPersistenceError, match="PETR4/ACAO"):
        await persist_asset_dividends_strict(db=db, collections=(_collection(),))

    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_conflicting_sources_for_same_global_identity() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    first = _collection(value=1.25, source="brapi")
    second = _collection(value=1.30, source="yfinance_history")
    combined = StrictDividendAssetCollection(
        ticker="PETR4",
        asset_type="ACAO",
        sources=(first.sources[0], second.sources[0]),
    )
    db = _db(assets=[asset])

    with pytest.raises(
        DividendsSeedPersistenceError,
        match=(
            r"valores divergentes: value_per_unit "
            r"\(brapi=1\.25, yfinance_history=1\.3\)"
        ),
    ):
        await persist_asset_dividends_strict(db=db, collections=(combined,))

    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconciles_equivalent_sources_ignoring_provenance_payload() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    first = _collection(
        source="brapi",
        raw_payload={"rate": 1.25, "provider_field": "primary"},
    )
    second = _collection(
        source="yfinance_history",
        record_date=None,
        raw_payload={"rate": 1.25},
    )
    combined = StrictDividendAssetCollection(
        ticker="PETR4",
        asset_type="ACAO",
        sources=(first.sources[0], second.sources[0]),
    )
    db = _db(assets=[asset])

    result = await persist_asset_dividends_strict(db=db, collections=(combined,))

    assert result.created == 1
    assert result.unchanged == 1
    created = db.add.call_args.args[0]
    assert created.source == "brapi"
    assert created.raw_payload == {
        "rate": 1.25,
        "provider_field": "primary",
    }


@pytest.mark.asyncio
async def test_reconciles_numeric_difference_within_storage_precision() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    first = _collection(value=1.250000001, source="brapi")
    second = _collection(value=1.250000009, source="yfinance_history")
    combined = StrictDividendAssetCollection(
        ticker="PETR4",
        asset_type="ACAO",
        sources=(first.sources[0], second.sources[0]),
    )
    db = _db(assets=[asset])

    result = await persist_asset_dividends_strict(db=db, collections=(combined,))

    assert result.created == 1
    assert result.unchanged == 1


@pytest.mark.asyncio
async def test_rejects_conflicting_dates_and_reports_exact_field() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    first = _collection(source="brapi")
    second = _collection(source="yfinance_history", payment_date=date(2026, 8, 11))
    combined = StrictDividendAssetCollection(
        ticker="PETR4",
        asset_type="ACAO",
        sources=(first.sources[0], second.sources[0]),
    )
    db = _db(assets=[asset])

    with pytest.raises(
        DividendsSeedPersistenceError,
        match=(
            r"valores divergentes: payment_date "
            r"\(brapi=2026-08-10, yfinance_history=2026-08-11\)"
        ),
    ):
        await persist_asset_dividends_strict(db=db, collections=(combined,))

    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_distinct_global_identities_remain_separate_events() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    first = _collection(source="brapi")
    second_event = ParsedDividendEvent(
        record_date=date(2026, 7, 25),
        ex_date=date(2026, 7, 28),
        payment_date=date(2026, 8, 10),
        approved_on=None,
        value_per_unit=1.25,
        dividend_type="DIVIDENDO",
        raw_payload={"rate": 1.25},
    )
    second_source = StrictDividendSourceCollection(
        source="yfinance_history",
        raw_rows=1,
        normalized_rows=(second_event,),
        rejected_rows=0,
        empty_reason=None,
    )
    combined = StrictDividendAssetCollection(
        ticker="PETR4",
        asset_type="ACAO",
        sources=(first.sources[0], second_source),
    )
    db = _db(assets=[asset])

    result = await persist_asset_dividends_strict(db=db, collections=(combined,))

    assert result.created == 2
    assert db.add.call_count == 2


@pytest.mark.asyncio
async def test_same_source_same_dates_distinct_values_are_separate_occurrences() -> None:
    asset = SimpleNamespace(id=7, ticker="AFLT3", asset_type="ACAO")
    first = ParsedDividendEvent(
        record_date=date(2024, 4, 10),
        ex_date=date(2024, 4, 11),
        payment_date=date(2024, 12, 20),
        approved_on=date(2024, 4, 10),
        value_per_unit=0.113784574,
        dividend_type="DIVIDENDO",
        raw_payload={"rate": 0.113784574},
    )
    second = ParsedDividendEvent(
        record_date=date(2024, 4, 10),
        ex_date=date(2024, 4, 11),
        payment_date=date(2024, 12, 20),
        approved_on=date(2024, 4, 10),
        value_per_unit=0.3413537,
        dividend_type="DIVIDENDO",
        raw_payload={"rate": 0.3413537},
    )
    source = StrictDividendSourceCollection(
        source="brapi",
        raw_rows=2,
        normalized_rows=(first, second),
        rejected_rows=0,
        empty_reason=None,
    )
    collection = StrictDividendAssetCollection(
        ticker="AFLT3",
        asset_type="ACAO",
        sources=(source,),
    )
    db = _db(assets=[asset])

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 2
    assert result.updated == 0
    assert db.add.call_count == 2
    created_values = {call.args[0].value_per_unit for call in db.add.call_args_list}
    assert created_values == {0.113784574, 0.3413537}


@pytest.mark.asyncio
async def test_lock_contention_is_blocking_before_any_query_or_write() -> None:
    db = _db(acquired=False)

    with pytest.raises(DividendsSeedAlreadyRunningError):
        await persist_asset_dividends_strict(db=db, collections=(_collection(),))

    db.execute.assert_not_awaited()
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
