from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.models.user import User
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_class_snapshot_service import (
    _load_exact_treasury_prices,
    _load_treasury_prices_with_holiday_carry,
    rebuild_class_snapshots,
)


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


@pytest.mark.asyncio
async def test_canonical_totals_preserves_transaction_asset_type_when_ticker_collides() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        user = User(email="col@test.local", hashed_password="x", name="Col", is_active=True)
        db.add(user)
        await db.flush()
        portfolio = Portfolio(user_id=user.id, name="Colisao", is_active=True)
        db.add(portfolio)
        await db.flush()

        btc_acao = Asset(ticker="BTC", name="BTC Equity", asset_type="ACAO", currency="BRL")
        btc_cripto = Asset(ticker="BTC", name="Bitcoin", asset_type="CRIPTO", currency="BRL")
        db.add_all([btc_acao, btc_cripto])
        await db.flush()

        db.add(
            Transaction(
                portfolio_id=portfolio.id,
                ticker="BTC",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("2"),
                price=Decimal("30.00"),
                fx_rate=Decimal("1"),
                price_brl=Decimal("30.00"),
                date=date(2026, 10, 26),
                currency="BRL",
            )
        )
        db.add_all(
            [
                AssetPrice(
                    asset_id=btc_acao.id,
                    timestamp=datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc),
                    close=Decimal("35.00"),
                    source="brapi_v2_stocks",
                ),
                AssetPrice(
                    asset_id=btc_cripto.id,
                    timestamp=datetime(2026, 10, 26, 0, 0, tzinfo=timezone.utc),
                    close=Decimal("400000.00"),
                    source="brapi_crypto",
                ),
            ]
        )
        await db.commit()

        totals = await calculate_canonical_portfolio_totals(
            db,
            portfolio.id,
            date(2026, 10, 26),
        )
        assert totals["market_value"] == Decimal("70.00")
        assert totals["market_value_by_class"] == {AssetType.ACAO.value: Decimal("70.00")}

    await engine.dispose()


@pytest.mark.asyncio
async def test_load_exact_treasury_prices_resolves_utc_midnight_and_prior_close() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        td = Asset(
            ticker="tesouro-renda-mais-2065",
            name="Tesouro Renda+ 2065",
            asset_type="TESOURO_DIRETO",
            currency="BRL",
        )
        db.add(td)
        await db.flush()
        db.add(
            AssetPrice(
                asset_id=td.id,
                timestamp=datetime(2026, 11, 11, 0, 0, tzinfo=timezone.utc),
                close=Decimal("166.85"),
                source="tesouro_transparente",
            )
        )
        await db.commit()

        prices_exact = await _load_exact_treasury_prices(
            db,
            ["TESOURO-RENDA-MAIS-2065"],
            date(2026, 11, 11),
        )
        prices_carry = await _load_treasury_prices_with_holiday_carry(
            db,
            ["TESOURO-RENDA-MAIS-2065"],
            date(2026, 11, 12),
        )
        assert prices_exact == {"TESOURO-RENDA-MAIS-2065": Decimal("166.85")}
        assert prices_carry == {"TESOURO-RENDA-MAIS-2065": Decimal("166.85")}

    await engine.dispose()
