from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_seed_treasury_price_service import (
    seed_synthetic_treasury_price,
)
from app.models.asset_price import AssetPrice


def _owned_treasury(*, currency: str = "BRL") -> SimpleNamespace:
    return SimpleNamespace(
        id=303,
        ticker="CERT303-TESOURO-SELIC-2029",
        asset_type="TESOURO_DIRETO",
        name="SGI certification #303 synthetic asset [TESOURO-SELIC-2029]",
        provider="synthetic-certification",
        provider_symbol="TESOURO-SELIC-2029",
        provider_status="synthetic-owned",
        currency=currency,
    )


def _execute_result(*, scalar=None, scalars=None) -> MagicMock:
    result = MagicMock()
    if scalar is not None:
        result.scalar_one_or_none.return_value = scalar
    if scalars is not None:
        result.scalars.return_value.all.return_value = scalars
    return result


def _canonical_price() -> SimpleNamespace:
    return SimpleNamespace(
        asset_id=303,
        timestamp=datetime(2026, 2, 28, tzinfo=timezone.utc),
        close=Decimal("13900.00"),
        source="synthetic-certification",
        open=None,
        high=None,
        low=None,
        volume=None,
    )


@pytest.mark.asyncio
async def test_seed_creates_one_dedicated_treasury_price() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=_owned_treasury()),
            _execute_result(scalars=[]),
        ]
    )

    result = await seed_synthetic_treasury_price(db)

    assert result.created == 1
    assert result.reused == 0
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    added = db.add.call_args.args[0]
    assert isinstance(added, AssetPrice)
    assert added.asset_id == 303
    assert added.timestamp == datetime(2026, 2, 28, tzinfo=timezone.utc)
    assert added.close == Decimal("13900.00")
    assert added.source == "synthetic-certification"


@pytest.mark.asyncio
async def test_seed_replay_reuses_exact_treasury_price() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=_owned_treasury()),
            _execute_result(scalars=[_canonical_price()]),
        ]
    )

    result = await seed_synthetic_treasury_price(db)

    assert result.created == 0
    assert result.reused == 1
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_treasury_price_contamination() -> None:
    contaminated = _canonical_price()
    contaminated.source = "brapi_treasury"
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=_owned_treasury()),
            _execute_result(scalars=[contaminated]),
        ]
    )

    with pytest.raises(
        SyntheticSeedContractError,
        match="synthetic treasury price collision for CERT303-TESOURO-SELIC-2029",
    ):
        await seed_synthetic_treasury_price(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_non_brl_treasury_asset() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(side_effect=[_execute_result(scalar=_owned_treasury(currency="USD"))])

    with pytest.raises(
        SyntheticSeedContractError,
        match="CERT303-TESOURO-SELIC-2029 must use BRL currency",
    ):
        await seed_synthetic_treasury_price(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()
