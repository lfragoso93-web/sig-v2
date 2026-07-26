from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.pre_prod_macro_seed_contract import MACRO_SEED_INDICATORS
from app.services.pre_prod_macro_seed_inspection import inspect_macro_seed_state


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)

    def one(self):
        assert len(self._rows) == 1
        return self._rows[0]


@pytest.mark.asyncio
async def test_inspection_collects_counts_coverage_duplicates_and_unsupported() -> None:
    db = SimpleNamespace()
    db.scalar = AsyncMock(return_value=11)

    executions = [
        _Result([SimpleNamespace(indicator="INPC")]),
    ]
    for index, indicator in enumerate(MACRO_SEED_INDICATORS, start=1):
        executions.extend(
            [
                _Result(
                    [
                        SimpleNamespace(
                            rows=index,
                            first_date=date(2020, 1, index),
                            last_date=date(2026, 7, index),
                        )
                    ]
                ),
                _Result(
                    [SimpleNamespace(rows=2)] if indicator == "CDI" else []
                ),
            ]
        )
    db.execute = AsyncMock(side_effect=executions)

    state = await inspect_macro_seed_state(db)

    assert state.total_rows == 11
    assert state.unsupported_indicators == ("INPC",)
    assert tuple(item.indicator for item in state.indicators) == MACRO_SEED_INDICATORS
    assert state.indicators[0].rows == 1
    assert state.indicators[0].first_date == "2020-01-01"
    assert state.indicators[0].last_date == "2026-07-01"
    assert state.indicators[0].duplicate_rows == 1
    assert all(item.duplicate_rows == 0 for item in state.indicators[1:])
    assert db.scalar.await_count == 1
    assert db.execute.await_count == 1 + (2 * len(MACRO_SEED_INDICATORS))


@pytest.mark.asyncio
async def test_inspection_supports_empty_rate_history() -> None:
    db = SimpleNamespace()
    db.scalar = AsyncMock(return_value=0)

    executions = [_Result([])]
    for _indicator in MACRO_SEED_INDICATORS:
        executions.extend(
            [
                _Result(
                    [SimpleNamespace(rows=0, first_date=None, last_date=None)]
                ),
                _Result([]),
            ]
        )
    db.execute = AsyncMock(side_effect=executions)

    state = await inspect_macro_seed_state(db)

    assert state.total_rows == 0
    assert state.unsupported_indicators == ()
    assert all(item.rows == 0 for item in state.indicators)
    assert all(item.first_date is None for item in state.indicators)
    assert all(item.last_date is None for item in state.indicators)
    assert all(item.duplicate_rows == 0 for item in state.indicators)
