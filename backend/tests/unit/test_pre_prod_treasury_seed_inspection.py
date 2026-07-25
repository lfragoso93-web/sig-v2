from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.pre_prod_treasury_seed_inspection import inspect_treasury_seed_state


class _CoverageResult:
    def __init__(self, row: tuple[object, object, int]):
        self._row = row

    def one(self) -> tuple[object, object, int]:
        return self._row


@pytest.mark.asyncio
async def test_inspection_reports_counts_integrity_and_coverage() -> None:
    db = AsyncMock()
    db.scalar.side_effect = [
        12,   # assets
        2,    # aliases
        1488, # prices
        0,    # orphan_prices
        0,    # duplicate_prices
        0,    # legacy_assets
        0,    # legacy_prices
    ]
    db.execute.return_value = _CoverageResult(
        (
            datetime(2024, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 7, 24, tzinfo=timezone.utc),
            12,
        )
    )

    counts, coverage = await inspect_treasury_seed_state(db)

    assert counts.assets == 12
    assert counts.aliases == 2
    assert counts.prices == 1488
    assert counts.orphan_prices == 0
    assert counts.duplicate_prices == 0
    assert counts.legacy_assets == 0
    assert counts.legacy_prices == 0
    assert coverage.first_price_date == "2024-01-02"
    assert coverage.last_price_date == "2026-07-24"
    assert coverage.priced_assets == 12
    assert db.scalar.await_count == 7
    db.commit.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspection_preserves_integrity_findings() -> None:
    db = AsyncMock()
    db.scalar.side_effect = [10, 4, 900, 3, 2, 1, 7]
    db.execute.return_value = _CoverageResult((None, None, 0))

    counts, coverage = await inspect_treasury_seed_state(db)

    assert counts.orphan_prices == 3
    assert counts.duplicate_prices == 2
    assert counts.legacy_assets == 1
    assert counts.legacy_prices == 7
    assert coverage.first_price_date is None
    assert coverage.last_price_date is None
    assert coverage.priced_assets == 0
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_inspection_normalizes_null_aggregates_to_zero() -> None:
    db = AsyncMock()
    db.scalar.side_effect = [None] * 7
    db.execute.return_value = _CoverageResult((None, None, 0))

    counts, coverage = await inspect_treasury_seed_state(db)

    assert counts.assets == 0
    assert counts.aliases == 0
    assert counts.prices == 0
    assert counts.orphan_prices == 0
    assert counts.duplicate_prices == 0
    assert counts.legacy_assets == 0
    assert counts.legacy_prices == 0
    assert coverage.priced_assets == 0
