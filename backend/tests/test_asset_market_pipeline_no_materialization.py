"""Regressões da contração da materialização no pipeline de mercado."""
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.asset import AssetType
from app.services.asset_market_pipeline_service import sync_asset_market_data


@pytest.mark.asyncio
async def test_pipeline_sincroniza_eventos_sem_materializar_direitos() -> None:
    db = Mock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    asset = Mock()

    with (
        patch(
            "app.services.asset_market_pipeline_service._get_or_create_asset",
            new=AsyncMock(return_value=(asset, False, False)),
        ),
        patch(
            "app.services.asset_market_pipeline_service.run_backfill",
            new=AsyncMock(),
        ) as run_backfill,
    ):
        result = await sync_asset_market_data(
            db=db,
            ticker="PETR4",
            asset_type=AssetType.ACAO,
            sync_prices=False,
            sync_logo=False,
            sync_events=True,
            materialize=True,
            commit=True,
        )

    run_backfill.assert_awaited_once_with(db, "PETR4", AssetType.ACAO)
    assert result.events_synced is True
    assert result.materialized == 0
    assert "materialization_disabled" in result.skipped_steps
    db.commit.assert_awaited_once()
