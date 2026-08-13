from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import treasury_legacy_identity_service as service


class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        proxy = MagicMock()
        proxy.all.return_value = list(self._rows)
        return proxy


@pytest.mark.asyncio
async def test_consolidation_moves_price_creates_alias_and_removes_legacy(monkeypatch):
    monkeypatch.setattr(
        service,
        "LEGACY_EDUCA_IDENTITIES",
        (("legacy", "canonical"),),
    )
    canonical = SimpleNamespace(id=2801, ticker="canonical")
    legacy = SimpleNamespace(id=13, ticker="legacy")
    price = SimpleNamespace(asset_id=13, timestamp="2026-08-07T12:00:00Z")

    monkeypatch.setattr(
        service,
        "_asset_by_ticker",
        AsyncMock(side_effect=[canonical, legacy]),
    )
    monkeypatch.setattr(service, "_count_blockers", AsyncMock(return_value=0))
    ensure_alias = AsyncMock(return_value=True)
    monkeypatch.setattr(service, "_ensure_alias", ensure_alias)

    tx_result = SimpleNamespace(rowcount=0)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarsResult([price]), tx_result])
    db.scalar = AsyncMock(return_value=0)
    db.delete = AsyncMock()

    result = await service.consolidate_legacy_educa_identities(db)

    assert result.consolidated == 1
    assert result.migrated_prices == 1
    assert result.created_aliases == 1
    assert result.errors == 0
    assert price.asset_id == 2801
    ensure_alias.assert_awaited_once()
    db.delete.assert_awaited_once_with(legacy)


@pytest.mark.asyncio
async def test_consolidation_refuses_blocked_legacy_before_alias_or_delete(monkeypatch):
    monkeypatch.setattr(
        service,
        "LEGACY_EDUCA_IDENTITIES",
        (("legacy", "canonical"),),
    )
    canonical = SimpleNamespace(id=2801, ticker="canonical")
    legacy = SimpleNamespace(id=13, ticker="legacy")

    monkeypatch.setattr(
        service,
        "_asset_by_ticker",
        AsyncMock(side_effect=[canonical, legacy]),
    )
    monkeypatch.setattr(service, "_count_blockers", AsyncMock(return_value=1))
    ensure_alias = AsyncMock(return_value=True)
    monkeypatch.setattr(service, "_ensure_alias", ensure_alias)

    db = MagicMock()
    db.delete = AsyncMock()

    result = await service.consolidate_legacy_educa_identities(db)

    assert result.consolidated == 0
    assert result.errors == 1
    ensure_alias.assert_not_awaited()
    db.delete.assert_not_awaited()
