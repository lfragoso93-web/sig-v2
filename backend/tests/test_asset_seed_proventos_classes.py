"""Matriz das classes nacionais catalogadas pelo seed de ativos."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.services.asset_seed_service import run_asset_seed


@pytest.mark.asyncio
async def test_seed_enriches_existing_national_dividend_classes(db: AsyncSession):
    db.add_all(
        [
            Asset(ticker="PETR4", asset_type=AssetType.ACAO.value, currency="BRL"),
            Asset(ticker="MXRF11", asset_type=AssetType.FII.value, currency="BRL"),
            Asset(ticker="BOVA11", asset_type=AssetType.ETF_NACIONAL.value, currency="BRL"),
            Asset(ticker="AAPL34", asset_type=AssetType.BDR.value, currency="BRL"),
        ]
    )
    await db.commit()

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
            "app.services.asset_seed_service.fetch_supported_crypto_universe",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await run_asset_seed(db)

    rows = (
        await db.execute(
            select(Asset.ticker, Asset.asset_type, Asset.name).order_by(Asset.ticker)
        )
    ).all()

    assert rows == [
        ("AAPL34", "BDR", "Apple BDR"),
        ("BOVA11", "ETF_NACIONAL", "Ibovespa ETF"),
        ("MXRF11", "FII", "Maxi Renda"),
        ("PETR4", "ACAO", "Petrobras"),
    ]
    assert result.created == 0
    assert result.updated == 4
    assert result.errors == 0
    assert result.by_type["ACAO"] == 0
    assert result.by_type["FII"] == 0
    assert result.by_type["ETF_NACIONAL"] == 0
    assert result.by_type["BDR"] == 0


@pytest.mark.asyncio
async def test_seed_does_not_create_missing_b3_assets_from_brapi(db: AsyncSession):
    with (
        patch(
            "app.services.asset_seed_service.fetch_all_tickers_v2",
            new_callable=AsyncMock,
            return_value=[{"stock": "PETR4", "name": "Petrobras"}],
        ),
        patch(
            "app.services.asset_seed_service.fetch_supported_crypto_universe",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await run_asset_seed(db)

    rows = (await db.execute(select(Asset))).scalars().all()

    assert rows == []
    assert result.created == 0
    assert result.updated == 0
    assert result.skipped >= 1


@pytest.mark.asyncio
async def test_seed_can_exclude_crypto_for_isolated_b3_stage(db: AsyncSession):
    with (
        patch(
            "app.services.asset_seed_service.fetch_all_tickers_v2",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.asset_seed_service.fetch_supported_crypto_universe",
            new_callable=AsyncMock,
        ) as crypto,
    ):
        await run_asset_seed(
            db,
            include_crypto=False,
        )

    crypto.assert_not_awaited()
