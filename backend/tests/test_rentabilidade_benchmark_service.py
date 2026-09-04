from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.rentabilidade_benchmark_service import (
    _compound_percent,
    _period_start,
    get_persisted_monthly_benchmarks,
)


def test_compound_percent_uses_effective_monthly_return() -> None:
    result = _compound_percent([Decimal("1.0"), Decimal("1.0")])
    assert result == 2.01


def test_period_start_keeps_requested_month_count() -> None:
    assert _period_start(12, date(2026, 7, 16)) == date(2025, 8, 1)


def test_period_start_zero_means_full_history() -> None:
    assert _period_start(0, date(2026, 7, 16)) is None


@pytest.mark.asyncio
async def test_monthly_benchmarks_reads_persisted_ibov_history(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="IBOV",
        name="Ibovespa",
        asset_type=AssetType.OUTRO.value,
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    db.add_all(
        [
            AssetPrice(
                asset_id=asset.id,
                timestamp=datetime(2026, 6, 30, tzinfo=timezone.utc),
                close=Decimal("100000"),
                source="b3_cotahist",
            ),
            AssetPrice(
                asset_id=asset.id,
                timestamp=datetime(2026, 7, 31, tzinfo=timezone.utc),
                close=Decimal("110000"),
                source="b3_cotahist",
            ),
        ]
    )
    await db.commit()

    result = await get_persisted_monthly_benchmarks(
        db,
        months=2,
        end_date=date(2026, 7, 31),
    )

    assert result["availability"]["IBOV"] == {
        "available": True,
        "status": "available",
    }
    assert result["points"] == [
        {
            "period": "2026-07",
            "ibov_monthly_pct": 10.0,
            "cdi_monthly_pct": None,
            "ipca_monthly_pct": None,
        }
    ]
