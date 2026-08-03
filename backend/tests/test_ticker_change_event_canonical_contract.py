from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent
from app.services.ticker_change_event_service import register_ticker_change
from app.services.ticker_resolution_service import ResolvedTicker


@pytest.mark.asyncio
async def test_register_ticker_change_populates_canonical_required_fields() -> None:
    current_asset = Asset(ticker="AUAU3", asset_type="ACAO", currency="BRL")
    current_asset.id = 6000
    old_asset = Asset(ticker="PETZ3", asset_type="ACAO", currency="BRL")
    old_asset.id = 4888

    result_current = Mock()
    result_current.scalar_one_or_none.return_value = current_asset
    result_alias = Mock()
    result_alias.scalar_one_or_none.return_value = SimpleNamespace(id=1)
    result_event = Mock()
    result_event.scalar_one_or_none.return_value = None

    db = AsyncMock()
    db.execute.side_effect = [result_current, result_alias, result_event]
    db.add = Mock()

    resolution = ResolvedTicker(
        requested_ticker="PETZ3",
        current_ticker="AUAU3",
        changed=True,
        status="renamed",
        effective_date=date(2026, 1, 5),
    )

    event = await register_ticker_change(
        db,
        portfolio_id=48,
        old_asset=old_asset,
        resolution=resolution,
    )

    assert isinstance(event, CorporateEvent)
    assert event.reconciliation_status == "UNRECONCILED"
    assert event.requires_review is True
    assert event.source_provider == "ticker_resolution"
    assert event.source_event_id == "ticker-change:48:PETZ3:AUAU3:2026-01-05"
    assert event.is_canonical is True
    assert event.effective_date == date(2026, 1, 5)
    assert event.quantity_factor == 1
    assert event.currency == "BRL"
    db.flush.assert_awaited_once()
