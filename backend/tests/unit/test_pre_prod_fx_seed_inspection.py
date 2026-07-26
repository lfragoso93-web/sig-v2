from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.pre_prod_fx_seed_inspection import inspect_fx_seed_state


@pytest.mark.asyncio
async def test_inspect_fx_seed_state_is_read_only_and_maps_database_state() -> None:
    db = AsyncMock()
    db.scalar.return_value = 4

    unsupported_result = Mock()
    unsupported_result.all.return_value = [SimpleNamespace(pair="EUR-BRL")]

    aggregate_result = Mock()
    aggregate_result.one.return_value = SimpleNamespace(
        rows=3,
        first_date=date(2026, 1, 2),
        last_date=date(2026, 1, 6),
    )

    duplicate_result = Mock()
    duplicate_result.all.return_value = [SimpleNamespace(rows=2)]

    db.execute.side_effect = [
        unsupported_result,
        aggregate_result,
        duplicate_result,
    ]

    state = await inspect_fx_seed_state(db)

    assert state.total_rows == 4
    assert state.unsupported_pairs == ("EUR-BRL",)
    assert len(state.pairs) == 1
    assert state.pairs[0].pair == "USD-BRL"
    assert state.pairs[0].rows == 3
    assert state.pairs[0].first_date == "2026-01-02"
    assert state.pairs[0].last_date == "2026-01-06"
    assert state.pairs[0].duplicate_rows == 1
    assert state.duplicate_rows == 1

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspect_fx_seed_state_handles_empty_table() -> None:
    db = AsyncMock()
    db.scalar.return_value = None

    unsupported_result = Mock()
    unsupported_result.all.return_value = []

    aggregate_result = Mock()
    aggregate_result.one.return_value = SimpleNamespace(
        rows=0,
        first_date=None,
        last_date=None,
    )

    duplicate_result = Mock()
    duplicate_result.all.return_value = []

    db.execute.side_effect = [
        unsupported_result,
        aggregate_result,
        duplicate_result,
    ]

    state = await inspect_fx_seed_state(db)

    assert state.total_rows == 0
    assert state.unsupported_pairs == ()
    assert state.pairs[0].rows == 0
    assert state.pairs[0].first_date is None
    assert state.pairs[0].last_date is None
    assert state.pairs[0].duplicate_rows == 0
