from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.integrations.bcb_ptax_strict import StrictPtaxRate
from app.services.pre_prod_fx_seed_preparation import (
    FxSeedPreparationError,
    prepare_pre_prod_fx_seed,
)


def _rate(day: int, value: str) -> StrictPtaxRate:
    return StrictPtaxRate(
        pair="USD-BRL",
        rate_date=date(2026, 7, day),
        rate=Decimal(value),
        quoted_at=datetime(2026, 7, day, 13, 0),
    )


@pytest.mark.asyncio
async def test_prepare_persists_every_rate_without_owning_transaction() -> None:
    db = object()
    fetch_runner = AsyncMock(return_value=(_rate(25, "5.50"), _rate(24, "5.40")))
    persist_runner = AsyncMock()

    result = await prepare_pre_prod_fx_seed(
        db,
        start_date="2026-07-24",
        end_date="2026-07-25",
        fetch_runner=fetch_runner,
        persist_runner=persist_runner,
    )

    fetch_runner.assert_awaited_once_with(date(2026, 7, 24), date(2026, 7, 25))
    assert persist_runner.await_count == 2
    assert persist_runner.await_args_list[0].args == (
        db,
        "2026-07-24",
        Decimal("5.40"),
    )
    assert persist_runner.await_args_list[0].kwargs == {"commit": False}
    assert persist_runner.await_args_list[1].args == (
        db,
        "2026-07-25",
        Decimal("5.50"),
    )
    assert persist_runner.await_args_list[1].kwargs == {"commit": False}

    assert result.pair == "USD-BRL"
    assert result.fetched_rows == 2
    assert result.persisted_rows == 2
    assert result.first_date == "2026-07-24"
    assert result.last_date == "2026-07-25"
    assert result.imported_counts() == {"USD-BRL": 2}


@pytest.mark.asyncio
async def test_prepare_rejects_reversed_period_before_fetch() -> None:
    fetch_runner = AsyncMock()
    persist_runner = AsyncMock()

    with pytest.raises(
        FxSeedPreparationError,
        match="start_date não pode ser posterior a end_date",
    ):
        await prepare_pre_prod_fx_seed(
            object(),
            start_date="2026-07-25",
            end_date="2026-07-24",
            fetch_runner=fetch_runner,
            persist_runner=persist_runner,
        )

    fetch_runner.assert_not_awaited()
    persist_runner.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_rejects_empty_fetch_without_persistence() -> None:
    fetch_runner = AsyncMock(return_value=())
    persist_runner = AsyncMock()

    with pytest.raises(
        FxSeedPreparationError,
        match="não retornou taxas",
    ):
        await prepare_pre_prod_fx_seed(
            object(),
            start_date="2026-07-24",
            end_date="2026-07-25",
            fetch_runner=fetch_runner,
            persist_runner=persist_runner,
        )

    persist_runner.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_rejects_duplicate_dates_without_persistence() -> None:
    fetch_runner = AsyncMock(
        return_value=(_rate(24, "5.40"), _rate(24, "5.41"))
    )
    persist_runner = AsyncMock()

    with pytest.raises(
        FxSeedPreparationError,
        match="data duplicada: 2026-07-24",
    ):
        await prepare_pre_prod_fx_seed(
            object(),
            start_date="2026-07-24",
            end_date="2026-07-25",
            fetch_runner=fetch_runner,
            persist_runner=persist_runner,
        )

    persist_runner.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_rejects_rows_outside_requested_period() -> None:
    fetch_runner = AsyncMock(return_value=(_rate(23, "5.30"),))
    persist_runner = AsyncMock()

    with pytest.raises(
        FxSeedPreparationError,
        match="fora do período solicitado: 2026-07-23",
    ):
        await prepare_pre_prod_fx_seed(
            object(),
            start_date="2026-07-24",
            end_date="2026-07-25",
            fetch_runner=fetch_runner,
            persist_runner=persist_runner,
        )

    persist_runner.assert_not_awaited()
