from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.models.user import User
from app.services.portfolio_class_snapshot_service import rebuild_class_snapshots


@pytest.mark.asyncio
async def test_rebuild_class_snapshots_handles_weekend_non_crypto_transaction() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        user = User(email="wknd@test.local", hashed_password="x", name="Wknd", is_active=True)
        db.add(user)
        await db.flush()
        portfolio = Portfolio(user_id=user.id, name="Emergencia", is_active=True)
        db.add(portfolio)
        await db.flush()

        petr = Asset(ticker="PETR4", name="Petrobras", asset_type="ACAO", currency="BRL")
        db.add(petr)
        await db.flush()

        # Saturday 2026-10-24 -> effective next business date 2026-10-26
        db.add(
            Transaction(
                portfolio_id=portfolio.id,
                ticker="PETR4",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("10"),
                price=Decimal("40.00"),
                fx_rate=Decimal("1"),
                price_brl=Decimal("40.00"),
                date=date(2026, 10, 24),
                currency="BRL",
            )
        )
        db.add(
            AssetPrice(
                asset_id=petr.id,
                timestamp=datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc),
                close=Decimal("41.00"),
                source="brapi_v2_stocks",
            )
        )
        await db.commit()

        count = await rebuild_class_snapshots(
            db,
            portfolio.id,
            end_date=date(2026, 10, 26),
        )
        assert count == 1

    await engine.dispose()
