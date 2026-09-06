from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.benchmark_rate_service import _upsert_rate_rows


def _daily_row(*, source: str = "BCB_SGS") -> dict:
    return {
        "indicator": "CDI",
        "date": date(2026, 2, 27),
        "value": Decimal("0.05"),
        "value_field": "rate_daily",
        "source": source,
    }


@pytest.mark.asyncio
async def test_official_upsert_rejects_nonofficial_input_source() -> None:
    db = SimpleNamespace(execute=AsyncMock())

    with pytest.raises(ValueError, match="nonofficial source"):
        await _upsert_rate_rows(
            db,
            [_daily_row(source="synthetic-certification")],
        )

    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_official_upsert_fails_when_identity_is_owned_by_nonofficial_row() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(rowcount=0))
    )

    with pytest.raises(RuntimeError, match="collision with nonofficial persisted source"):
        await _upsert_rate_rows(db, [_daily_row()])

    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_official_upsert_accepts_insert_or_owned_update() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(rowcount=1))
    )

    count = await _upsert_rate_rows(db, [_daily_row()])

    assert count == 1
    db.execute.assert_awaited_once()
