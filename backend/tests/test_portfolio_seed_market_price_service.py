from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_seed_market_price_service import (
    SYNTHETIC_MARKET_PRICE_SOURCE,
    seed_generic_market_prices,
)

GENERIC_ASSETS = [
    ("PETR4", "ACAO", Decimal("24.00")),
    ("MXRF11", "FII", Decimal("10.50")),
    ("BOVA11", "ETF_NACIONAL", Decimal("112.00")),
    ("AAPL34", "BDR", Decimal("38.00")),
    ("BTC", "CRIPTO", Decimal("210000.00")),
]


def _owned_asset(index: int, source_ticker: str, asset_type: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=3000 + index,
        ticker=f"CERT303-{source_ticker}",
        asset_type=asset_type,
        name=f"SGI certification #303 synthetic asset [{source_ticker}]",
        provider="synthetic-certification",
        provider_symbol=source_ticker,
        provider_status="synthetic-owned",
    )


def _asset_results() -> list[MagicMock]:
    results = []
    for index, (source_ticker, asset_type, _) in enumerate(GENERIC_ASSETS):
        result = MagicMock()
        result.scalar_one_or_none.return_value = _owned_asset(index, source_ticker, asset_type)
        results.append(result)
    return results


def _price_result(rows: list[SimpleNamespace]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_seed_generic_market_prices_creates_only_five_generic_prices() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(side_effect=[*_asset_results(), _price_result([])])

    result = await seed_generic_market_prices(db)

    assert result.created == 5
    assert result.reused == 0
    assert db.add.call_count == 5
    db.commit.assert_awaited_once()

    created = [call.args[0] for call in db.add.call_args_list]
    assert {row.asset_id for row in created} == {3000, 3001, 3002, 3003, 3004}
    assert {Decimal(row.close) for row in created} == {
        Decimal("24.00"),
        Decimal("10.50"),
        Decimal("112.00"),
        Decimal("38.00"),
        Decimal("210000.00"),
    }
    assert {row.source for row in created} == {SYNTHETIC_MARKET_PRICE_SOURCE}
    assert {row.timestamp for row in created} == {
        datetime(2026, 2, 28, tzinfo=timezone.utc)
    }
    assert all(row.open is None for row in created)
    assert all(row.high is None for row in created)
    assert all(row.low is None for row in created)
    assert all(row.volume is None for row in created)


@pytest.mark.asyncio
async def test_seed_generic_market_prices_replay_reuses_all_rows() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    timestamp = datetime(2026, 2, 28, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(
            asset_id=3000 + index,
            timestamp=timestamp,
            close=close,
            source=SYNTHETIC_MARKET_PRICE_SOURCE,
            open=None,
            high=None,
            low=None,
            volume=None,
        )
        for index, (_, _, close) in enumerate(GENERIC_ASSETS)
    ]
    db.execute = AsyncMock(side_effect=[*_asset_results(), _price_result(rows)])

    result = await seed_generic_market_prices(db)

    assert result.created == 0
    assert result.reused == 5
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_generic_market_prices_fails_closed_on_existing_price_collision() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    collision = SimpleNamespace(
        asset_id=3000,
        timestamp=datetime(2026, 2, 28, tzinfo=timezone.utc),
        close=Decimal("23.99"),
        source=SYNTHETIC_MARKET_PRICE_SOURCE,
        open=None,
        high=None,
        low=None,
        volume=None,
    )
    db.execute = AsyncMock(
        side_effect=[*_asset_results(), _price_result([collision])]
    )

    with pytest.raises(
        SyntheticSeedContractError,
        match="synthetic market price collision for CERT303-PETR4",
    ):
        await seed_generic_market_prices(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_generic_market_prices_fails_closed_when_owned_asset_is_missing() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=missing)

    with pytest.raises(
        SyntheticSeedContractError,
        match="must be seeded before prices",
    ):
        await seed_generic_market_prices(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()
