from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.integrations.bcb_ptax_strict import StrictPtaxError, StrictPtaxRate
from app.models.fx_rate import FxRate
from app.services import fx_rate_sync_service
from app.services.fx_rate_sync_service import sync_usd_brl_fx_rates


@pytest.mark.asyncio
async def test_sync_usd_brl_fx_rates_inserts_and_updates_idempotently(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        db.add(FxRate(pair="USD-BRL", rate_date=date(2026, 11, 4), rate=Decimal("5.47000000")))
        await db.commit()

        async def fake_fetch(start_date, end_date):
            assert start_date == date(2026, 11, 1)
            assert end_date == date(2026, 11, 12)
            return (
                StrictPtaxRate(
                    pair="USD-BRL",
                    rate_date=date(2026, 11, 4),
                    rate=Decimal("5.47780000"),
                    quoted_at=datetime(2026, 11, 4, 16, 0, tzinfo=timezone.utc),
                ),
                StrictPtaxRate(
                    pair="USD-BRL",
                    rate_date=date(2026, 11, 11),
                    rate=Decimal("5.75120000"),
                    quoted_at=datetime(2026, 11, 11, 16, 0, tzinfo=timezone.utc),
                ),
            )

        monkeypatch.setattr(fx_rate_sync_service, "fetch_strict_usd_brl_period", fake_fetch)

        summary = await sync_usd_brl_fx_rates(db, end_date=date(2026, 11, 12))
        assert summary["inserted"] == 1
        assert summary["updated"] == 1
        assert summary["latest_date"] == "2026-11-11"

        rows = (await db.execute(select(FxRate).order_by(FxRate.rate_date))).scalars().all()
        assert [(r.rate_date, r.rate) for r in rows] == [
            (date(2026, 11, 4), Decimal("5.47780000")),
            (date(2026, 11, 11), Decimal("5.75120000")),
        ]

    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_usd_brl_fx_rates_handles_unavailable_ptax_gracefully(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        async def fake_fail(start_date, end_date):
            raise StrictPtaxError("sem PTAX no feriado")

        monkeypatch.setattr(fx_rate_sync_service, "fetch_strict_usd_brl_period", fake_fail)

        summary = await sync_usd_brl_fx_rates(db, end_date=date(2026, 11, 12))
        assert summary["fetched"] == 0
        assert summary["inserted"] == 0
        assert "sem PTAX" in str(summary["warning"])

    await engine.dispose()
