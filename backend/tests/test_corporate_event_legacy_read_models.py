"""Valida os relatórios legacy com sessões assíncronas sintéticas."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.corporate_event_legacy_dry_run_service import (
    build_legacy_corporate_event_dry_run,
)
from app.services.corporate_event_legacy_inventory_service import (
    load_corporate_event_legacy_inventory,
)


class _ScalarResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def scalars(self) -> "_ScalarResult":
        return self

    def all(self) -> list[SimpleNamespace]:
        return list(self._rows)


class _AggregateResult:
    def __init__(self, row: tuple[int, ...]) -> None:
        self._row = row

    def one(self) -> tuple[int, ...]:
        return self._row


def _event(event_id: int, **overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": event_id,
        "ticker": "ABCD3",
        "event_type": "DESDOBRAMENTO",
        "source_event_id": f"legacy:{event_id}",
        "effective_date": object(),
        "quantity_factor": 2,
        "portfolio_id": None,
        "status": "PENDENTE",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_inventory_maps_aggregate_columns_without_mutation() -> None:
    db = SimpleNamespace(execute=AsyncMock(return_value=_AggregateResult((9, 7, 2, 1, 3, 4, 5))))

    inventory = await load_corporate_event_legacy_inventory(db)

    assert inventory.to_dict() == {
        "total_legacy": 9,
        "global_legacy": 7,
        "portfolio_bound_legacy": 2,
        "ignored_legacy": 1,
        "without_source_event_id": 3,
        "without_effective_date": 4,
        "without_quantity_factor": 5,
    }
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_dry_run_counts_and_samples_follow_database_order() -> None:
    rows = [
        _event(3),
        _event(8, effective_date=None),
        _event(11, portfolio_id=4),
        _event(15),
    ]
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(rows)))

    report = await build_legacy_corporate_event_dry_run(db, sample_limit=3)

    assert report.total == 4
    assert report.reconcilable == 2
    assert report.incomplete == 1
    assert report.blocked_review == 1
    assert [item.event_id for item in report.samples] == [3, 8, 11]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_dry_run_negative_sample_limit_returns_no_samples() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_ScalarResult([_event(1), _event(2)]))
    )

    report = await build_legacy_corporate_event_dry_run(db, sample_limit=-10)

    assert report.total == 2
    assert report.samples == ()
