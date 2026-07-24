from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.services import b3_historical_market_rebuild_service as service


class _FixtureSession:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *_args):
        return False


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

    async def fake_year(_year: int, _tickers: set[str]):
        return {
            "PETR4": [
                (datetime(2026, 7, 23, tzinfo=timezone.utc), 30.0),
                (datetime(2026, 7, 25, tzinfo=timezone.utc), 31.0),
            ]
        }

    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: _FixtureSession(db))
    monkeypatch.setattr(service, "fetch_b3_cotahist_year_bulk", fake_year)
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
