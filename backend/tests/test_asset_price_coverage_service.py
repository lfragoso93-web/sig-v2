import pytest
from datetime import date

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import (
    CoverageStatus,
    classify_coverage,
)


def test_no_quote_type_never_requires_market_sync() -> None:
    status = classify_coverage(
        asset_type=AssetType.RENDA_FIXA,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.NO_MARKET_QUOTE


def test_treasury_uses_dedicated_provider_pipeline() -> None:
    status = classify_coverage(
        asset_type=AssetType.TESOURO_DIRETO,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.DEDICATED_PROVIDER


def test_missing_asset_is_reported_before_price_coverage() -> None:
    status = classify_coverage(
        asset_type=AssetType.ACAO,
        asset_exists=False,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.MISSING_ASSET


def test_asset_without_prices_is_missing() -> None:
    status = classify_coverage(
        asset_type=AssetType.FII,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=None,
        last_price_date=None,
    )

    assert status == CoverageStatus.MISSING


def test_history_missing_at_start_is_partial_start() -> None:
    status = classify_coverage(
        asset_type=AssetType.ETF_NACIONAL,
        asset_exists=True,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=date(2025, 1, 1),
        last_price_date=date(2026, 7, 10),
    )

    assert status == CoverageStatus.PARTIAL_START


def test_old_last_price_is_stale() -> None:
    status = classify_coverage(
        asset_type=AssetType.STOCK,
        asset_exists=True,
        required_from=date(2025, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=date(2024, 1, 1),
        last_price_date=date(2026, 6, 30),
    )

    assert status == CoverageStatus.STALE


def test_missing_both_edges_is_partial_both() -> None:
    status = classify_coverage(
        asset_type=AssetType.CRIPTO,
        asset_exists=True,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 13),
        first_price_date=date(2025, 1, 1),
        last_price_date=date(2026, 6, 1),
    )

    assert status == CoverageStatus.PARTIAL_BOTH


def test_small_calendar_gap_is_complete() -> None:
    status = classify_coverage(
        asset_type=AssetType.ACAO,
        asset_exists=True,
        required_from=date(2025, 1, 4),
        required_to=date(2026, 7, 13),
        first_price_date=date(2025, 1, 6),
        last_price_date=date(2026, 7, 10),
    )

    assert status == CoverageStatus.COMPLETE


def test_daily_close_mode_detects_d1_lag_without_start_gaps() -> None:
    status = classify_coverage(
        asset_type=AssetType.ETF_INTERNACIONAL,
        asset_exists=True,
        required_from=date(2026, 11, 11),
        required_to=date(2026, 11, 11),
        first_price_date=date(2014, 2, 4),
        last_price_date=date(2026, 11, 10),
        end_grace_days=0,
        include_start_gaps=False,
    )

    assert status == CoverageStatus.STALE


@pytest.mark.asyncio
async def test_audit_asset_price_coverage_bypasses_end_unavailable_when_requested(monkeypatch) -> None:
    from datetime import datetime, timezone
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.database import Base
    from app.models.asset import Asset
    from app.models.asset_price import AssetPrice
    from app.models.transaction import OperationType, Transaction
    from app.models.user import User
    from app.models.portfolio import Portfolio
    from app.services.asset_price_coverage_service import audit_asset_price_coverage

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        user = User(email="cov@test.local", hashed_password="x", name="Cov", is_active=True)
        db.add(user)
        await db.flush()
        portfolio = Portfolio(user_id=user.id, name="Main", is_active=True)
        db.add(portfolio)
        await db.flush()
        fii = Asset(
            ticker="MXRF11",
            name="Maxi Renda",
            asset_type="FII",
            currency="BRL",
            provider_status="HISTORY_END_UNAVAILABLE",
            provider_last_sync_at=datetime(2026, 11, 11, 23, 45, tzinfo=timezone.utc),
        )
        db.add(fii)
        await db.flush()
        db.add(
            Transaction(
                portfolio_id=portfolio.id,
                ticker="MXRF11",
                asset_type="FII",
                operation=OperationType.buy,
                quantity=10,
                price=9.0,
                date=date(2026, 11, 10),
                currency="BRL",
            )
        )
        db.add(
            AssetPrice(
                asset_id=fii.id,
                timestamp=datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc),
                close=8.75,
                source="b3_cotahist",
            )
        )
        await db.commit()

        suppressed = await audit_asset_price_coverage(
            db,
            required_to=date(2026, 11, 11),
            full_history=False,
            history_start=date(2026, 11, 10),
            end_grace_days=0,
            include_start_gaps=False,
        )
        assert [c for c in suppressed if c.ticker == "MXRF11"][0].needs_sync is False

        retried = await audit_asset_price_coverage(
            db,
            required_to=date(2026, 11, 11),
            full_history=False,
            history_start=date(2026, 11, 10),
            end_grace_days=0,
            include_start_gaps=False,
            ignore_end_unavailable=True,
        )
        assert [c for c in retried if c.ticker == "MXRF11"][0].needs_sync is True

    await engine.dispose()
