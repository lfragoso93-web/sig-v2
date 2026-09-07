from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from app.models.asset import AssetType
from app.services import portfolio_canonical_valuation_service as valuation


def test_average_price_is_derived_from_snapshot_cost_and_quantity() -> None:
    state = SimpleNamespace(qty=Decimal("0.50"), cost=Decimal("7000.00"))

    assert valuation._average_price_from_state(state) == Decimal("14000.0")


def test_average_price_is_zero_for_zero_quantity() -> None:
    state = SimpleNamespace(qty=Decimal("0"), cost=Decimal("0"))

    assert valuation._average_price_from_state(state) == Decimal("0")


@pytest.mark.asyncio
async def test_treasury_correction_preserves_persisted_ticker_case_for_same_identity(
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
    get_price = AsyncMock(return_value=13900.0)
    monkeypatch.setattr(valuation, "build_positions_at", build_positions)
    monkeypatch.setattr(valuation, "resolve_treasury_symbol", resolve_symbol)
    monkeypatch.setattr(valuation, "get_price_at_date", get_price)

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
    get_price.assert_awaited_once_with(
        ANY,
        "CERT303-TESOURO-SELIC-2029",
        AssetType.TESOURO_DIRETO,
        "2026-02-28",
    )


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
    get_price = AsyncMock(return_value=13900.0)
    monkeypatch.setattr(valuation, "build_positions_at", build_positions)
    monkeypatch.setattr(valuation, "resolve_treasury_symbol", resolve_symbol)
    monkeypatch.setattr(valuation, "get_price_at_date", get_price)

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
    get_price.assert_awaited_once_with(
        ANY,
        "tesouro-selic-2029",
        AssetType.TESOURO_DIRETO,
        "2026-02-28",
    )
