from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.routers import fx
from app.services.fx_rate_reader import PersistedFxRate, USD_BRL_PAIR


@pytest.mark.asyncio
async def test_usd_brl_route_returns_persisted_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    persisted = PersistedFxRate(
        pair=USD_BRL_PAIR,
        rate_date=date(2026, 8, 5),
        rate=Decimal("5.43210000"),
    )
    loader = AsyncMock(return_value=persisted)
    monkeypatch.setattr(fx, "load_latest_usd_brl_rate", loader)

    db = object()
    response = await fx.usd_brl_rate(db)

    assert response == {
        "rate": 5.4321,
        "pair": "USDBRL",
        "rate_date": "2026-08-05",
        "source": "persisted_fx_rates",
    }
    loader.assert_awaited_once_with(db)


@pytest.mark.asyncio
async def test_usd_brl_route_exposes_absence_without_fixed_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fx,
        "load_latest_usd_brl_rate",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await fx.usd_brl_rate(object())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Cotação USD/BRL persistida indisponível."
