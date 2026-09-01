from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.b3_cotahist import CotahistRecord
from app.models.asset import Asset, AssetType
from app.services.b3_cotahist_catalog_service import upsert_b3_cotahist_catalog


def _record(
    *,
    ticker: str = "ALOS3",
    market_type: str = "010",
    short_name: str = "ALLOS",
    specification: str = "ON      NM",
    currency: str = "R$",
    isin: str | None = "BRALOSACNOR5",
) -> CotahistRecord:
    return CotahistRecord(
        timestamp=datetime(2026, 8, 28, tzinfo=timezone.utc),
        ticker=ticker,
        market_type=market_type,
        short_name=short_name,
        specification=specification,
        currency=currency,
        open=Decimal("10.00"),
        high=Decimal("11.00"),
        low=Decimal("9.50"),
        close=Decimal("10.50"),
        volume=Decimal("100000.00"),
        quotation_factor=1,
        isin=isin,
    )


@pytest.mark.asyncio
async def test_cotahist_catalog_creates_supported_b3_assets(db: AsyncSession) -> None:
    result = await upsert_b3_cotahist_catalog(
        db,
        [
            _record(ticker="ALOS3", specification="ON      NM"),
            _record(ticker="MXRF11", short_name="FII MAXI", specification="CI"),
            _record(ticker="BOVA11", short_name="ISHARES BOVA", specification="CI"),
            _record(ticker="AAPL34", specification="BDR     N1", isin="BRAAPLBDR004"),
        ],
    )
    await db.commit()

    rows = (
        await db.execute(
            select(Asset.ticker, Asset.asset_type, Asset.currency).order_by(Asset.ticker)
        )
    ).all()

    assert rows == [
        ("AAPL34", AssetType.BDR.value, "BRL"),
        ("ALOS3", AssetType.ACAO.value, "BRL"),
        ("BOVA11", AssetType.ETF_NACIONAL.value, "BRL"),
        ("MXRF11", AssetType.FII.value, "BRL"),
    ]
    assert result.created == 4
    assert result.updated == 0
    assert result.by_type == {
        "ACAO": 1,
        "FII": 1,
        "ETF_NACIONAL": 1,
        "BDR": 1,
    }


@pytest.mark.asyncio
async def test_cotahist_catalog_is_idempotent_per_ticker_and_type(db: AsyncSession) -> None:
    records = [
        _record(ticker="ALOS3", specification="ON      NM"),
        _record(ticker="ALOS3", specification="ON      NM"),
    ]

    first = await upsert_b3_cotahist_catalog(db, records)
    await db.commit()
    second = await upsert_b3_cotahist_catalog(db, records)
    await db.commit()

    count = await db.scalar(
        select(func.count()).select_from(Asset).where(Asset.ticker == "ALOS3")
    )
    assert count == 1
    assert first.created == 1
    assert first.skipped == 1
    assert second.created == 0
    assert second.skipped == 2


@pytest.mark.asyncio
async def test_cotahist_catalog_preserves_existing_enrichment(db: AsyncSession) -> None:
    db.add(
        Asset(
            ticker="ALOS3",
            name="Allos Friendly Name",
            asset_type=AssetType.ACAO.value,
            currency="BRL",
            sector="Shoppings",
            logo_url="https://example.test/logo.png",
            isin_code="BRALOSACNOR5",
        )
    )
    await db.commit()

    result = await upsert_b3_cotahist_catalog(
        db,
        [
            _record(
                ticker="ALOS3",
                short_name="ALLOS B3",
                specification="ON      NM",
                isin="BRALOSACNOR5",
            )
        ],
    )
    await db.commit()

    asset = (
        await db.execute(select(Asset).where(Asset.ticker == "ALOS3"))
    ).scalar_one()

    assert result.skipped == 1
    assert asset.name == "Allos Friendly Name"
    assert asset.sector == "Shoppings"
    assert asset.logo_url == "https://example.test/logo.png"


@pytest.mark.asyncio
async def test_cotahist_catalog_fills_only_missing_baseline_fields(db: AsyncSession) -> None:
    db.add(
        Asset(
            ticker="ALOS3",
            name=None,
            asset_type=AssetType.ACAO.value,
            currency="",
            isin_code=None,
        )
    )
    await db.commit()

    result = await upsert_b3_cotahist_catalog(
        db,
        [_record(ticker="ALOS3", short_name="ALLOS", specification="ON      NM")],
    )
    await db.commit()

    asset = (
        await db.execute(select(Asset).where(Asset.ticker == "ALOS3"))
    ).scalar_one()

    assert result.updated == 1
    assert asset.name == "ALLOS"
    assert asset.currency == "BRL"
    assert asset.isin_code == "BRALOSACNOR5"


@pytest.mark.asyncio
async def test_cotahist_catalog_skips_ineligible_and_unresolved_records(db: AsyncSession) -> None:
    result = await upsert_b3_cotahist_catalog(
        db,
        [
            _record(ticker="PETR1", specification="DIR ORD"),
            _record(ticker="ABCD11", short_name="ALPHA", specification="CI"),
        ],
    )
    await db.commit()

    count = await db.scalar(select(func.count()).select_from(Asset))
    assert count == 0
    assert result.ineligible == 1
    assert result.unresolved == 1
