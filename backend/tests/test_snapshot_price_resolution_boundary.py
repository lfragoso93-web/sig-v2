from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services.snapshot_price_resolution_service import (
    SnapshotPriceRequirement,
    SnapshotPriceUnavailableError,
    resolve_missing_snapshot_prices,
)


SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "snapshot_price_resolution_service.py"
)
SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "portfolio_snapshot_service.py"
)


@pytest.mark.asyncio
async def test_returns_only_fully_persisted_prices() -> None:
    requirements = [
        SnapshotPriceRequirement("PETR4", AssetType.ACAO),
        SnapshotPriceRequirement("VALE3", AssetType.ACAO),
    ]
    db = AsyncMock()

    result = await resolve_missing_snapshot_prices(
        db,
        requirements,
        "2026-08-07",
        {"PETR4": 31.50, "VALE3": 68.25},
    )

    assert result == {"PETR4": 31.50, "VALE3": 68.25}


@pytest.mark.asyncio
async def test_unresolved_price_fails_explicitly() -> None:
    db = AsyncMock()
    with pytest.raises(SnapshotPriceUnavailableError, match="PETR4"):
        await resolve_missing_snapshot_prices(
            db,
            [SnapshotPriceRequirement("PETR4", AssetType.ACAO)],
            "2026-08-07",
            {"PETR4": None},
        )


def test_snapshot_consumer_has_no_broad_prefetch_or_price_proxy() -> None:
    source = SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert "_prefetch_price_history" not in source
    assert "persist_daily_prices" not in source
    assert "usando avg_price como proxy" not in source
    assert "state.avg_price" not in source
    assert "resolve_missing_snapshot_prices" in source


def test_resolution_service_has_no_broad_history_fetch() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    assert "persist_daily_prices" not in source
    assert "period=\"max\"" not in source
    assert "avg_price" not in source
