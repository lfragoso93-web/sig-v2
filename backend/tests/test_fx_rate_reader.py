from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.fx_rate_reader import (
    USD_BRL_PAIR,
    PersistedFxRate,
    load_latest_fx_rate,
    load_latest_usd_brl_rate,
)


@pytest.mark.asyncio
async def test_load_latest_fx_rate_returns_persisted_decimal() -> None:
    row = SimpleNamespace(
        id=7,
        pair=USD_BRL_PAIR,
        rate_date=date(2026, 8, 5),
        rate=Decimal("5.43210000"),
    )
    result = SimpleNamespace(scalar_one_or_none=lambda: row)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    loaded = await load_latest_fx_rate(db, pair=USD_BRL_PAIR)

    assert loaded == PersistedFxRate(
        pair=USD_BRL_PAIR,
        rate_date=date(2026, 8, 5),
        rate=Decimal("5.43210000"),
    )
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_latest_fx_rate_returns_none_without_coverage() -> None:
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    assert await load_latest_fx_rate(db, pair="EUR-BRL") is None


@pytest.mark.asyncio
async def test_usd_brl_reader_uses_canonical_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = PersistedFxRate(
        pair=USD_BRL_PAIR,
        rate_date=date(2026, 8, 5),
        rate=Decimal("5.40000000"),
    )
    loader = AsyncMock(return_value=expected)
    monkeypatch.setattr("app.services.fx_rate_reader.load_latest_fx_rate", loader)

    db = object()
    assert await load_latest_usd_brl_rate(db) == expected
    loader.assert_awaited_once_with(db, pair=USD_BRL_PAIR)
