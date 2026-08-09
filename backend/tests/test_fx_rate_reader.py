from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.fx_rate_reader import (
    USD_BRL_PAIR,
    PersistedFxRate,
    load_fx_rate_at_or_before,
    load_latest_fx_rate,
    load_latest_usd_brl_rate,
    load_usd_brl_rate_at_or_before,
    load_usd_brl_rates_for_dates,
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


@pytest.mark.asyncio
async def test_historical_reader_uses_last_fixing_at_or_before_date() -> None:
    row = SimpleNamespace(
        id=8,
        pair=USD_BRL_PAIR,
        rate_date=date(2026, 8, 7),
        rate=Decimal("5.51000000"),
    )
    result = SimpleNamespace(scalar_one_or_none=lambda: row)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    loaded = await load_fx_rate_at_or_before(
        db,
        pair=USD_BRL_PAIR,
        target_date=date(2026, 8, 9),
    )

    assert loaded == PersistedFxRate(
        pair=USD_BRL_PAIR,
        rate_date=date(2026, 8, 7),
        rate=Decimal("5.51000000"),
    )
    sql = str(db.execute.await_args.args[0])
    assert "fx_rates.rate_date <=" in sql


@pytest.mark.asyncio
async def test_batch_reader_returns_only_dates_with_persisted_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = AsyncMock(
        side_effect=[
            PersistedFxRate(USD_BRL_PAIR, date(2026, 8, 1), Decimal("5.10")),
            None,
        ]
    )
    monkeypatch.setattr(
        "app.services.fx_rate_reader.load_usd_brl_rate_at_or_before",
        loader,
    )

    first = date(2026, 8, 2)
    second = date(2026, 8, 3)
    loaded = await load_usd_brl_rates_for_dates(object(), [second, first, first])

    assert loaded == {
        first: PersistedFxRate(USD_BRL_PAIR, date(2026, 8, 1), Decimal("5.10"))
    }
    assert loader.await_count == 2


@pytest.mark.asyncio
async def test_usd_brl_historical_shortcut_uses_canonical_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = PersistedFxRate(
        USD_BRL_PAIR,
        date(2026, 8, 7),
        Decimal("5.51"),
    )
    loader = AsyncMock(return_value=expected)
    monkeypatch.setattr("app.services.fx_rate_reader.load_fx_rate_at_or_before", loader)

    db = object()
    target = date(2026, 8, 9)
    assert await load_usd_brl_rate_at_or_before(db, target) == expected
    loader.assert_awaited_once_with(
        db, pair=USD_BRL_PAIR, target_date=target
    )
