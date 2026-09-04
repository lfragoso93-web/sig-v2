from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.b3_cotahist import CotahistRecord
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services import b3_historical_market_rebuild_service as service


class _FixtureSession:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *_args):
        return False


def _record(
    *,
    ticker: str = "PETR4",
    day: int = 23,
    market_type: str = "010",
    close: str = "30.00",
) -> CotahistRecord:
    close_value = Decimal(close)
    return CotahistRecord(
        timestamp=datetime(2026, 7, day, tzinfo=timezone.utc),
        ticker=ticker,
        market_type=market_type,
        short_name="PETROBRAS",
        specification="PN      N2",
        currency="R$",
        open=close_value - Decimal("1.00"),
        high=close_value + Decimal("2.00"),
        low=close_value - Decimal("2.00"),
        close=close_value,
        volume=Decimal("123456.78"),
        quotation_factor=1,
        isin="BRPETRACNPR6",
    )


@pytest.mark.asyncio
async def test_cotahist_is_idempotent_and_respects_cutoff(db: AsyncSession, monkeypatch):
    db.add(
        Asset(
            ticker="PETR4",
            name="Petrobras",
            asset_type=AssetType.ACAO.value,
            currency="BRL",
        )
    )
    await db.commit()

    async def fake_year(_year: int):
        return [_record(day=23, close="30.00"), _record(day=25, close="31.00")]

    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: _FixtureSession(db))
    monkeypatch.setattr(service, "fetch_b3_cotahist_year_records", fake_year)
    monkeypatch.setattr(service, "refresh_asset_last_prices", AsyncMock(return_value=1))

    first = await service.rebuild_b3_historical_market(
        2026,
        2026,
        cutoff_date=date(2026, 7, 24),
    )
    second = await service.rebuild_b3_historical_market(
        2026,
        2026,
        cutoff_date=date(2026, 7, 24),
    )

    assert first.rows_inserted == 1
    assert second.rows_inserted == 0


@pytest.mark.asyncio
async def test_cotahist_persists_ohlcv_and_prefers_standard_market(
    db: AsyncSession,
    monkeypatch,
):
    db.add(
        Asset(
            ticker="PETR4",
            name="Petrobras",
            asset_type=AssetType.ACAO.value,
            currency="BRL",
        )
    )
    await db.commit()

    async def fake_year(_year: int):
        return [
            _record(day=23, market_type="020", close="29.00"),
            _record(day=23, market_type="010", close="30.00"),
        ]

    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: _FixtureSession(db))
    monkeypatch.setattr(service, "fetch_b3_cotahist_year_records", fake_year)
    monkeypatch.setattr(service, "refresh_asset_last_prices", AsyncMock(return_value=1))

    result = await service.rebuild_b3_historical_market(
        2026,
        2026,
        cutoff_date=date(2026, 7, 24),
    )

    price = (await db.execute(select(AssetPrice))).scalar_one()

    assert result.rows_received == 1
    assert result.rows_inserted == 1
    assert price.open == Decimal("29.00000000")
    assert price.high == Decimal("32.00000000")
    assert price.low == Decimal("28.00000000")
    assert price.close == Decimal("30.00000000")
    assert price.volume == Decimal("123456.78")
    assert price.source == "b3_cotahist"


@pytest.mark.asyncio
async def test_cotahist_materializes_ibov_benchmark_history(
    db: AsyncSession,
    monkeypatch,
):
    async def fake_year(_year: int):
        return [
            _record(ticker="IBOV", day=23, close="125000.00"),
            _record(ticker="PETR4", day=23, close="30.00"),
        ]

    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: _FixtureSession(db))
    monkeypatch.setattr(service, "fetch_b3_cotahist_year_records", fake_year)
    monkeypatch.setattr(service, "refresh_asset_last_prices", AsyncMock(return_value=1))

    result = await service.rebuild_b3_historical_market(
        2026,
        2026,
        cutoff_date=date(2026, 7, 24),
    )

    asset = (
        await db.execute(select(Asset).where(Asset.ticker == "IBOV"))
    ).scalar_one()
    price = (
        await db.execute(select(AssetPrice).where(AssetPrice.asset_id == asset.id))
    ).scalar_one()

    assert asset.asset_type == AssetType.OUTRO.value
    assert asset.provider == "b3_cotahist"
    assert asset.provider_status == "persisted_benchmark"
    assert result.rows_received == 1
    assert result.rows_inserted == 1
    assert price.close == Decimal("125000.00000000")
    assert price.source == "b3_cotahist"
