from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.models.dividend import DividendType
from app.models.transaction import OperationType
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
    materialized_result = Mock()
    materialized_result.all.return_value = [
        ("ACAO", DividendType.DIVIDENDO, "brapi", 2026, "PETR4", 3),
    ]
    db.execute.side_effect = [global_result, materialized_result]

    result = await inspect_dividends_seed_groupings(db)

    assert result == (
        {
            "asset_class": "ACAO",
            "event_type": "DIVIDENDO",
            "source": "brapi",
            "year": 2026,
            "ticker": "PETR4",
            "global_events": 2,
            "materialized_rights": 3,
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
        40,  # transactions
        3,  # portfolios
        20,  # asset_dividends
        15,  # dividends
        1,  # sync_jobs
        2,  # portfolios_with_dividends
        1,  # orphan_asset_dividends
        2,  # orphan_dividend_events
        3,  # orphan_dividend_portfolios
        4,  # missing_ex_dates
        5,  # negative_global_values
        6,  # negative_materialized_values
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
    duplicate_materialization_result = Mock()
    duplicate_materialization_result.all.return_value = [
        SimpleNamespace(rows=2),
        SimpleNamespace(rows=4),
    ]
    events_result = Mock()
    events_result.all.return_value = [
        (
            101,
            date(2026, 7, 20),
            date(2026, 7, 21),
            DividendType.DIVIDENDO,
            "PETR4",
        ),
        (
            102,
            date(2026, 7, 20),
            date(2026, 7, 21),
            DividendType.BONIFICACAO,
            "PETR4",
        ),
    ]
    transactions_result = Mock()
    transactions_result.all.return_value = [
        (7, "petr4", date(2026, 7, 1), OperationType.buy, 10),
        (8, "PETR4", date(2026, 7, 1), OperationType.buy, 5),
    ]
    rights_result = Mock()
    rights_result.all.return_value = [
        (7, 101),
        (9, 101),
    ]
    db.execute.side_effect = [
        coverage_result,
        events_result,
        transactions_result,
        rights_result,
        duplicate_global_result,
        duplicate_materialization_result,
    ]

    counts, coverage, integrity = await inspect_dividends_seed_state(db)

    assert counts.assets == 12
    assert counts.transactions == 40
    assert counts.portfolios == 3
    assert counts.asset_dividends == 20
    assert counts.dividends == 15
    assert counts.sync_jobs == 1
    assert coverage.first_ex_date == "2020-01-02"
    assert coverage.last_ex_date == "2026-07-28"
    assert coverage.assets_with_events == 9
    assert coverage.portfolios_with_dividends == 2
    assert coverage.eligible_materializations == 2
    assert coverage.materialized_eligible_rights == 1
    assert integrity.duplicate_global_events == 2
    assert integrity.duplicate_materializations == 4
    assert integrity.orphan_asset_dividends == 1
    assert integrity.orphan_dividend_events == 2
    assert integrity.orphan_dividend_portfolios == 3
    assert integrity.missing_ex_dates == 4
    assert integrity.negative_monetary_values == 11
    assert integrity.missing_materializations == 1
    assert integrity.materializations_without_entitlement == 1

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.flush.assert_not_awaited()
    db.add.assert_not_called()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspection_handles_empty_tables_without_writes() -> None:
    db = _db_stub()
    db.scalar.side_effect = [0] * 13

    coverage_result = Mock()
    coverage_result.one.return_value = SimpleNamespace(
        first_ex_date=None,
        last_ex_date=None,
        assets_with_events=0,
    )
    no_duplicates = Mock()
    no_duplicates.all.return_value = []
    no_rows = Mock()
    no_rows.all.return_value = []
    db.execute.side_effect = [
        coverage_result,
        no_rows,
        no_rows,
        no_rows,
        no_duplicates,
        no_duplicates,
    ]

    counts, coverage, integrity = await inspect_dividends_seed_state(db)

    assert counts.asset_dividends == 0
    assert counts.dividends == 0
    assert coverage.first_ex_date is None
    assert coverage.last_ex_date is None
    assert integrity.blocking_findings == 0

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.flush.assert_not_awaited()
    db.add.assert_not_called()
    db.delete.assert_not_awaited()
