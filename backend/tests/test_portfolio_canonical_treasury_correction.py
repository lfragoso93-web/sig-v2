from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from app.models.asset import AssetType
from app.services import portfolio_canonical_valuation_service as valuation


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


def test_average_price_is_derived_from_snapshot_cost_and_quantity() -> None:
    state = SimpleNamespace(qty=Decimal("0.50"), cost=Decimal("7000.00"))

    assert valuation._average_price_from_state(state) == Decimal("14000.0")


def test_average_price_is_zero_for_zero_quantity() -> None:
    state = SimpleNamespace(qty=Decimal("0"), cost=Decimal("0"))

    assert valuation._average_price_from_state(state) == Decimal("0")


@pytest.mark.asyncio
async def test_treasury_correction_uses_persisted_ticker_for_same_identity(
    monkeypatch,
) -> None:
    positions = {
        "CERT303-TESOURO-SELIC-2029": SimpleNamespace(
            asset_type=AssetType.TESOURO_DIRETO,
            qty=Decimal("0.50"),
            cost=Decimal("7000.00"),
        )
    }
    build_positions = AsyncMock(return_value=positions)
    resolve_symbol = AsyncMock(return_value="cert303-tesouro-selic-2029")
    persisted_ticker = AsyncMock(return_value="cert303-tesouro-selic-2029")
    get_prices = AsyncMock(
        return_value={"cert303-tesouro-selic-2029": Decimal("13900.0")}
    )
    monkeypatch.setattr(valuation, "build_positions_at", build_positions)
    monkeypatch.setattr(valuation, "resolve_treasury_symbol", resolve_symbol)
    monkeypatch.setattr(valuation, "_persisted_treasury_ticker", persisted_ticker)
    monkeypatch.setattr(valuation, "_treasury_prices_at_or_before_batch", get_prices)

    result = await valuation._treasury_correction_at_date(
        AsyncMock(),
        portfolio_id=13,
        target_date=date(2026, 2, 28),
    )

    assert result == {
        "correction": Decimal("-50.00"),
        "matched": 1,
        "unresolved": 0,
    }
    resolve_symbol.assert_awaited_once_with(
        ANY,
        "CERT303-TESOURO-SELIC-2029",
    )
    persisted_ticker.assert_awaited_once_with(
        ANY,
        "cert303-tesouro-selic-2029",
    )
    get_prices.assert_awaited_once()
    assert get_prices.await_args.args[0] is not None
    assert get_prices.await_args.args[1] == ["cert303-tesouro-selic-2029"]
    assert get_prices.await_args.args[2] == date(2026, 2, 28)


@pytest.mark.asyncio
async def test_treasury_correction_uses_distinct_canonical_ticker_for_real_alias(
    monkeypatch,
) -> None:
    positions = {
        "Tesouro Selic 2029": SimpleNamespace(
            asset_type=AssetType.TESOURO_DIRETO,
            qty=Decimal("0.50"),
            cost=Decimal("7000.00"),
        )
    }
    build_positions = AsyncMock(return_value=positions)
    resolve_symbol = AsyncMock(return_value="tesouro-selic-2029")
    persisted_ticker = AsyncMock(return_value="tesouro-selic-2029")
    get_prices = AsyncMock(return_value={"tesouro-selic-2029": Decimal("13900.0")})
    monkeypatch.setattr(valuation, "build_positions_at", build_positions)
    monkeypatch.setattr(valuation, "resolve_treasury_symbol", resolve_symbol)
    monkeypatch.setattr(valuation, "_persisted_treasury_ticker", persisted_ticker)
    monkeypatch.setattr(valuation, "_treasury_prices_at_or_before_batch", get_prices)

    result = await valuation._treasury_correction_at_date(
        AsyncMock(),
        portfolio_id=13,
        target_date=date(2026, 2, 28),
    )

    assert result == {
        "correction": Decimal("-50.00"),
        "matched": 1,
        "unresolved": 0,
    }
    persisted_ticker.assert_awaited_once_with(ANY, "tesouro-selic-2029")
    get_prices.assert_awaited_once()
    assert get_prices.await_args.args[1] == ["tesouro-selic-2029"]
    assert get_prices.await_args.args[2] == date(2026, 2, 28)


@pytest.mark.asyncio
async def test_treasury_correction_reuses_symbol_and_ticker_caches(
    monkeypatch,
) -> None:
    positions = {
        "Tesouro Selic 2029": SimpleNamespace(
            asset_type=AssetType.TESOURO_DIRETO,
            qty=Decimal("0.50"),
            cost=Decimal("7000.00"),
        )
    }
    resolve_symbol = AsyncMock(return_value="tesouro-selic-2029")
    persisted_ticker = AsyncMock(return_value="tesouro-selic-2029")
    get_prices = AsyncMock(return_value={"tesouro-selic-2029": Decimal("13900.0")})
    monkeypatch.setattr(valuation, "resolve_treasury_symbol", resolve_symbol)
    monkeypatch.setattr(valuation, "_persisted_treasury_ticker", persisted_ticker)
    monkeypatch.setattr(valuation, "_treasury_prices_at_or_before_batch", get_prices)

    symbol_cache = {}
    ticker_cache = {}
    for target_date in (date(2026, 2, 28), date(2026, 3, 1)):
        await valuation._treasury_correction_at_date(
            AsyncMock(),
            portfolio_id=13,
            target_date=target_date,
            positions=positions,
            treasury_symbol_cache=symbol_cache,
            treasury_ticker_cache=ticker_cache,
        )

    resolve_symbol.assert_awaited_once_with(ANY, "Tesouro Selic 2029")
    persisted_ticker.assert_awaited_once_with(ANY, "tesouro-selic-2029")
    assert get_prices.await_count == 2


@pytest.mark.asyncio
async def test_treasury_price_batch_returns_latest_price_per_ticker() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_RowsResult(
            [
                ("tesouro-prefixado-2029", Decimal("830.00")),
                ("tesouro-selic-2029", Decimal("14050.00")),
            ]
        )
    )

    result = await valuation._treasury_prices_at_or_before_batch(
        db,
        ["TESOURO-SELIC-2029", "tesouro-prefixado-2029", "tesouro-selic-2029"],
        date(2026, 3, 1),
    )

    assert result == {
        "tesouro-prefixado-2029": Decimal("830.00"),
        "tesouro-selic-2029": Decimal("14050.00"),
    }
    db.execute.assert_awaited_once()
