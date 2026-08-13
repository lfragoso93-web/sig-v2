from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.asset import AssetType
from app.services import asset_price_global_backfill_service as global_prices
from app.services import treasury_price_history_service as treasury_history


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_treasury_history_repeated_upsert_uses_same_unique_identity(monkeypatch):
    asset = SimpleNamespace(
        id=7,
        ticker="tesouro-selic-2029",
        asset_type=AssetType.TESOURO_DIRETO.value,
        last_price=None,
        last_price_updated_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock()
    row = (datetime(2026, 8, 8, 12, tzinfo=timezone.utc), 123.45)

    first = await treasury_history._upsert_price_rows(db, asset, [row])
    second = await treasury_history._upsert_price_rows(db, asset, [row])

    assert first == 1
    assert second == 1
    assert db.execute.await_count == 2
    for call in db.execute.await_args_list:
        statement = call.args[0]
        assert "ON CONFLICT" in str(statement)
        assert "uq_price_asset_timestamp" in str(statement)


@pytest.mark.asyncio
async def test_global_asset_price_backfill_second_run_skips_when_coverage_is_complete(
    monkeypatch,
):
    db = MagicMock()
    monkeypatch.setattr(
        global_prices,
        "AsyncSessionLocal",
        lambda: _SessionContext(db),
    )
    complete_coverage = SimpleNamespace(
        asset_id=1,
        asset_type=AssetType.CRIPTO.value,
        ticker="BTC",
        needs_sync=False,
    )
    audit = AsyncMock(return_value=[complete_coverage])
    sync_candidates = AsyncMock(return_value=[])
    monkeypatch.setattr(global_prices, "audit_asset_price_coverage", audit)
    monkeypatch.setattr(global_prices, "_sync_candidates", sync_candidates)

    first = await global_prices.run_global_asset_price_backfill(
        required_to=date(2026, 8, 8)
    )
    second = await global_prices.run_global_asset_price_backfill(
        required_to=date(2026, 8, 8)
    )

    assert first["requested"] == 0
    assert first["inserted"] == 0
    assert second["requested"] == 0
    assert second["inserted"] == 0
    assert sync_candidates.await_count == 2
    assert all(call.args[0] == [] for call in sync_candidates.await_args_list)
