"""Behavior tests for persisted FX coverage in class snapshots."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.fx_rate_reader import PersistedFxRate, USD_BRL_PAIR
from app.services.portfolio_class_snapshot_service import (
    _load_required_usd_brl_rates,
)


@pytest.mark.asyncio
async def test_class_snapshot_preloads_persisted_fx_for_business_dates() -> None:
    db = AsyncMock()
    persisted = {
        date(2026, 8, 14): PersistedFxRate(
            pair=USD_BRL_PAIR,
            rate_date=date(2026, 8, 14),
            rate=Decimal("5.41000000"),
        ),
        date(2026, 8, 17): PersistedFxRate(
            pair=USD_BRL_PAIR,
            rate_date=date(2026, 8, 14),
            rate=Decimal("5.41000000"),
        ),
    }

    with patch(
        "app.services.portfolio_class_snapshot_service.load_usd_brl_rates_for_dates",
        return_value=persisted,
    ) as reader:
        result = await _load_required_usd_brl_rates(
            db,
            date(2026, 8, 14),
            date(2026, 8, 17),
        )

    reader.assert_awaited_once_with(
        db,
        [date(2026, 8, 14), date(2026, 8, 17)],
    )
    assert result == {
        date(2026, 8, 14): Decimal("5.41000000"),
        date(2026, 8, 17): Decimal("5.41000000"),
    }


@pytest.mark.asyncio
async def test_class_snapshot_fails_when_persisted_fx_is_missing() -> None:
    db = AsyncMock()

    with patch(
        "app.services.portfolio_class_snapshot_service.load_usd_brl_rates_for_dates",
        return_value={},
    ):
        with pytest.raises(
            RuntimeError,
            match="first_missing=2026-08-14 missing_dates=2",
        ):
            await _load_required_usd_brl_rates(
                db,
                date(2026, 8, 14),
                date(2026, 8, 17),
            )
