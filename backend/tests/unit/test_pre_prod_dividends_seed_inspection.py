from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.models.dividend_enums import DividendType
from app.services.pre_prod_dividends_seed_inspection import (
    inspect_dividends_seed_groupings,
    inspect_dividends_seed_state,
)


def _db_stub() -> SimpleNamespace:
    return SimpleNamespace(
        scalar=AsyncMock(),
        execute=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        flush=AsyncMock(),
        add=Mock(),
        delete=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_groupings_are_canonical_and_read_only() -> None:
    db = _db_stub()
    global_result = Mock()
    global_result.all.return_value = [
        ("ACAO", DividendType.DIVIDENDO, "brapi", 2026, "petr4", 2),
    ]
    db.execute.return_value = global_result

    result = await inspect_dividends_seed_groupings(db)

    assert result == (
        {
            "asset_class": "ACAO",
            "event_type": "DIVIDENDO",
            "source": "brapi",
            "year": 2026,
            "ticker": "PETR4",
            "global_events": 2,
        },
    )
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.flush.assert_not_awaited()
    db.add.assert_not_called()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspection_maps_state_and_never_writes() -> None:
    db = _db_stub()
    db.scalar.side_effect = [
        12,  # assets
        20,  # asset_dividends
        1,  # orphan_asset_dividends
        4,  # missing_ex_dates
        5,  # negative_global_values
    ]

    coverage_result = Mock()
    coverage_result.one.return_value = SimpleNamespace(
        first_ex_date=date(2020, 1, 2),
        last_ex_date=date(2026, 7, 28),
        assets_with_events=9,
    )
    duplicate_global_result = Mock()
    duplicate_global_result.all.return_value = [
        SimpleNamespace(rows=3),
    ]
    db.execute.side_effect = [
        coverage_result,
        duplicate_global_result,
    ]

    counts, coverage, integrity = await inspect_dividends_seed_state(db)

    assert counts.assets == 12
    assert counts.asset_dividends == 20
    assert not hasattr(counts, "sync_jobs")
    assert coverage.first_ex_date == "2020-01-02"
    assert coverage.last_ex_date == "2026-07-28"
    assert coverage.assets_with_events == 9
    assert integrity.duplicate_global_events == 2
    assert integrity.orphan_asset_dividends == 1
    assert integrity.missing_ex_dates == 4
    assert integrity.negative_monetary_values == 5

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.flush.assert_not_awaited()
    db.add.assert_not_called()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspection_handles_empty_tables_without_writes() -> None:
    db = _db_stub()
    db.scalar.side_effect = [0] * 5

    coverage_result = Mock()
    coverage_result.one.return_value = SimpleNamespace(
        first_ex_date=None,
        last_ex_date=None,
        assets_with_events=0,
    )
    no_duplicates = Mock()
    no_duplicates.all.return_value = []
    db.execute.side_effect = [
        coverage_result,
        no_duplicates,
    ]

    counts, coverage, integrity = await inspect_dividends_seed_state(db)

    assert counts.asset_dividends == 0
    assert coverage.first_ex_date is None
    assert coverage.last_ex_date is None
    assert integrity.blocking_findings == 0

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.flush.assert_not_awaited()
    db.add.assert_not_called()
    db.delete.assert_not_awaited()
