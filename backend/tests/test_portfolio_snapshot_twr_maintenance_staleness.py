from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import OperationType, Transaction
from app.models.user import User
from app.services.portfolio_snapshot_twr_maintenance_service import (
    _portfolio_needs_twr_rebuild,
)

_BRT = ZoneInfo("America/Sao_Paulo")


@pytest.mark.asyncio
async def test_portfolio_needs_rebuild_when_intraday_snapshot_precedes_close_or_new_price() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        user = User(email="snap@test.local", hashed_password="x", name="Snap", is_active=True)
        db.add(user)
        await db.flush()
        portfolio = Portfolio(user_id=user.id, name="Oficial", is_active=True)
        db.add(portfolio)
        await db.flush()

        asset = Asset(ticker="PETR4", name="Petrobras", asset_type="ACAO", currency="BRL")
        db.add(asset)
        await db.flush()

        db.add(
            Transaction(
                portfolio_id=portfolio.id,
                ticker="PETR4",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("10"),
                price=Decimal("40.00"),
                date=date(2026, 11, 12),
                currency="BRL",
            )
        )
        # Snapshot written during intraday (09:05 BRT = 12:05 UTC) on 2026-11-12
        db.add(
            PortfolioSnapshot(
                portfolio_id=portfolio.id,
                snapshot_date=date(2026, 11, 12),
                market_value=Decimal("435.50"),
                cost_basis=Decimal("400.00"),
                invested_total=Decimal("400.00"),
                daily_return_pct=Decimal("0.100000"),
                accumulated_return_pct=Decimal("8.875000"),
                dividends_accumulated=Decimal("0.00"),
                updated_at=datetime(2026, 11, 12, 12, 5, tzinfo=timezone.utc),
            )
        )
        await db.commit()

        # 1. At 21:00 BRT on 2026-11-12, an intraday snapshot from 09:05 BRT must trigger rebuild
        assert await _portfolio_needs_twr_rebuild(
            db,
            portfolio.id,
            now_brt=datetime(2026, 11, 12, 21, 0, tzinfo=_BRT),
        ) is True

        # 2. Once rebuilt at 21:05 BRT (00:05 UTC next day), no rebuild needed if no newer market data
        snap = (await db.execute(PortfolioSnapshot.__table__.select())).first()
        assert snap is not None
        await db.execute(
            PortfolioSnapshot.__table__.update()
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .values(updated_at=datetime(2026, 11, 13, 0, 5, tzinfo=timezone.utc))
        )
        await db.commit()
        assert await _portfolio_needs_twr_rebuild(
            db,
            portfolio.id,
            now_brt=datetime(2026, 11, 12, 21, 10, tzinfo=_BRT),
        ) is False

        # 3. If a late AssetPrice sync arrives afterwards (e.g., at 22:45 BRT = 01:45 UTC), rebuild triggers again
        db.add(
            AssetPrice(
                asset_id=asset.id,
                timestamp=datetime(2026, 11, 12, 3, 0, tzinfo=timezone.utc),
                close=Decimal("44.10"),
                source="brapi_v2_stocks",
            )
        )
        asset.provider_last_sync_at = datetime(2026, 11, 13, 1, 45, tzinfo=timezone.utc)
        await db.commit()
        assert await _portfolio_needs_twr_rebuild(
            db,
            portfolio.id,
            now_brt=datetime(2026, 11, 12, 23, 5, tzinfo=_BRT),
        ) is True

    await engine.dispose()
