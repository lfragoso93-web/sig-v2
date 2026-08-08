from pathlib import Path
from unittest.mock import AsyncMock, patch

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
async def test_resolves_only_missing_prices_with_point_gap_resolver() -> None:
    requirements = [
        SnapshotPriceRequirement("PETR4", AssetType.ACAO),
        SnapshotPriceRequirement("VALE3", AssetType.ACAO),
    ]
    db = AsyncMock()

    with patch(
        "app.services.snapshot_price_resolution_service.resolve_price_at_date_gap",
        new=AsyncMock(return_value=68.25),
    ) as resolver:
        result = await resolve_missing_snapshot_prices(
            db,
            requirements,
            "2026-08-07",
            {"PETR4": 31.50, "VALE3": None},
        )

    assert result == {"PETR4": 31.50, "VALE3": 68.25}
    resolver.assert_awaited_once_with(db, "VALE3", AssetType.ACAO, "2026-08-07")


@pytest.mark.asyncio
async def test_unresolved_price_fails_explicitly() -> None:
    db = AsyncMock()
    with patch(
        "app.services.snapshot_price_resolution_service.resolve_price_at_date_gap",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(SnapshotPriceUnavailableError, match="PETR4"):
            await resolve_missing_snapshot_prices(
                db,
                [SnapshotPriceRequirement("PETR4", AssetType.ACAO)],
                "2026-08-07",
                {"PETR4": None},
            )


def test_snapshot_legacy_prefetch_and_avg_price_proxy_are_still_tracked() -> None:
    """Caracteriza o desvio que o proximo commit deve remover do consumidor."""
    source = SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert "_prefetch_price_history" in source
    assert "persist_daily_prices" in source
    assert "usando avg_price como proxy" in source


def test_resolution_service_has_no_broad_history_fetch() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    assert "persist_daily_prices" not in source
    assert "period=\"max\"" not in source
    assert "avg_price" not in source
