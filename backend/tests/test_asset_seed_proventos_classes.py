"""Matriz das classes nacionais catalogadas pelo seed de ativos."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.asset_seed_service import run_asset_seed


@pytest.mark.asyncio
async def test_seed_catalogs_all_national_dividend_classes(db: AsyncSession):
    items_by_subtype = {
        "stock": [{"stock": "PETR4", "name": "Petrobras"}],
        "fii": [{"stock": "MXRF11", "name": "Maxi Renda"}],
        "etf": [{"stock": "BOVA11", "name": "Ibovespa ETF"}],
        "bdr": [{"stock": "AAPL34", "name": "Apple BDR"}],
    }

    async def fake_fetch(subtype: str):
        return items_by_subtype.get(subtype, [])

    with (
        patch(
            "app.services.asset_seed_service.fetch_all_tickers_v2",
            new_callable=AsyncMock,
            side_effect=fake_fetch,
        ),
        patch(
            "app.services.asset_seed_service.fetch_crypto_available_all",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await run_asset_seed(db, run_backfill=False)

    rows = (
        await db.execute(select(Asset.ticker, Asset.asset_type).order_by(Asset.ticker))
    ).all()

    assert rows == [
        ("AAPL34", "BDR"),
        ("BOVA11", "ETF_NACIONAL"),
        ("MXRF11", "FII"),
        ("PETR4", "ACAO"),
    ]
    assert result.created == 4
    assert result.errors == 0
    assert result.by_type["ACAO"] == 1
    assert result.by_type["FII"] == 1
    assert result.by_type["ETF_NACIONAL"] == 1
    assert result.by_type["BDR"] == 1


@pytest.mark.asyncio
async def test_seed_can_exclude_crypto_for_isolated_b3_stage(db: AsyncSession):
    with (
        patch(
            "app.services.asset_seed_service.fetch_all_tickers_v2",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.asset_seed_service.fetch_crypto_available_all",
            new_callable=AsyncMock,
        ) as crypto,
    ):
        await run_asset_seed(db, run_backfill=False, include_crypto=False)

    crypto.assert_not_awaited()
