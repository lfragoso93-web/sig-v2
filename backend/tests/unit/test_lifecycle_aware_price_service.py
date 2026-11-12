from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.lifecycle_aware_price_service import (
    _is_stale_price_usable,
    get_prices_at_date_with_lifecycle,
)


def test_stale_price_is_usable_inside_market_staleness_window() -> None:
    assert _is_stale_price_usable(
        last_price_date=date(2025, 10, 2),
        target_date=date(2025, 11, 25),
    )


def test_stale_price_is_not_usable_after_market_staleness_window() -> None:
    assert not _is_stale_price_usable(
        last_price_date=date(2025, 10, 2),
        target_date=date(2026, 1, 15),
    )


def test_future_price_is_not_usable_as_stale_fallback() -> None:
    assert not _is_stale_price_usable(
        last_price_date=date(2025, 10, 3),
        target_date=date(2025, 10, 2),
    )


@pytest.mark.asyncio
async def test_prices_at_date_never_look_ahead_to_next_day_and_isolate_class() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        bova = Asset(ticker="BOVA11", name="BOVA11", asset_type="ETF_NACIONAL", currency="BRL")
        btc_crypto = Asset(ticker="BTC", name="Bitcoin", asset_type="CRIPTO", currency="BRL")
        btc_acao = Asset(ticker="BTC", name="BTC Anomalo", asset_type="ACAO", currency="BRL")
        db.add_all([bova, btc_crypto, btc_acao])
        await db.flush()

        db.add_all([
            AssetPrice(
                asset_id=bova.id,
                timestamp=datetime(2026, 11, 10, 3, 0, tzinfo=timezone.utc),
                close=168.85,
                source="brapi_v2_stocks",
            ),
            AssetPrice(
                asset_id=bova.id,
                timestamp=datetime(2026, 11, 11, 3, 0, tzinfo=timezone.utc),
                close=169.50,
                source="brapi_v2_stocks",
            ),
            AssetPrice(
                asset_id=btc_crypto.id,
                timestamp=datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc),
                close=412000.0,
                source="brapi_v2_crypto_max",
            ),
        ])
        await db.commit()

        # Looking up 2026-11-10 must return 168.85, NOT 2026-11-11's 169.50
        prices_d0, pre_d0, gaps_d0 = await get_prices_at_date_with_lifecycle(
            db,
            [("BOVA11", AssetType.ETF_NACIONAL)],
            date(2026, 11, 10),
        )
        assert prices_d0 == {"BOVA11": 168.85}
        assert pre_d0 == set()
        assert gaps_d0 == set()

        # BTC/ACAO must not inherit BTC/CRIPTO price
        prices_acao, _, gaps_acao = await get_prices_at_date_with_lifecycle(
            db,
            [("BTC", AssetType.ACAO)],
            date(2026, 11, 10),
        )
        assert prices_acao == {}
        assert gaps_acao == {"BTC"}

    await engine.dispose()
