from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services import portfolio_canonical_valuation_service as service


@pytest.mark.asyncio
async def test_base_totals_fail_closed_on_real_market_price_gap(monkeypatch):
    state = SimpleNamespace(
        asset_type=AssetType.ACAO.value,
        qty=Decimal("10"),
        cost=Decimal("100"),
        realized_pnl=Decimal("0"),
        is_usd=False,
    )
    monkeypatch.setattr(
        service,
        "build_positions_at",
        AsyncMock(return_value={"CERT303-GAP": state}),
    )
    monkeypatch.setattr(
        service,
        "get_prices_at_date_with_lifecycle",
        AsyncMock(return_value=({}, set(), {"CERT303-GAP"})),
    )

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(all=lambda: [])

    with pytest.raises(RuntimeError, match="CERT303-GAP"):
        await service._base_totals_without_dedicated_lookup(
            db, 303, date(2026, 2, 28)
        )


@pytest.mark.asyncio
async def test_base_totals_allows_pre_listing_cost_proxy(monkeypatch):
    state = SimpleNamespace(
        asset_type=AssetType.ACAO.value,
        qty=Decimal("10"),
        cost=Decimal("100"),
        realized_pnl=Decimal("0"),
        is_usd=False,
    )
    monkeypatch.setattr(
        service,
        "build_positions_at",
        AsyncMock(return_value={"CERT303-PRE": state}),
    )
    monkeypatch.setattr(
        service,
        "get_prices_at_date_with_lifecycle",
        AsyncMock(return_value=({}, {"CERT303-PRE"}, set())),
    )

    asset_result = SimpleNamespace(all=lambda: [])
    invested_result = SimpleNamespace(scalar_one=lambda: Decimal("100"))
    db = AsyncMock()
    db.execute.side_effect = [asset_result, invested_result]

    totals = await service._base_totals_without_dedicated_lookup(
        db, 303, date(2026, 2, 28)
    )

    assert totals["market_value"] == Decimal("100.00")
    assert totals["pre_listing_assets"] == 1
    assert totals["real_price_gaps"] == 0
