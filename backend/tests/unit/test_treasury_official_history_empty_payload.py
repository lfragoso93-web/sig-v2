from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import treasury_official_history_service as service


@pytest.mark.asyncio
async def test_empty_catalog_result_keeps_complete_history_contract(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    monkeypatch.setattr(
        service,
        "_canonical_assets",
        AsyncMock(return_value=({}, {}, ["titulo-sem-alias"])),
    )

    result = await service._rebuild_official_treasury_history(db, commit=False)

    assert result == {
        "official_symbols": 0,
        "matched_assets": 0,
        "imported": 0,
        "official_imported": 0,
        "fallback_imported": 0,
        "official_covered": 0,
        "fallback_symbols": 0,
        "empty_payloads": 0,
        "last_prices_refreshed": 0,
        "primary_source": "tesouro_transparente",
        "fallback_source": "brapi_treasury",
        "alias_groups": 0,
        "aliases": {},
        "unresolved_assets": ["titulo-sem-alias"],
        "history": {},
    }
    db.commit.assert_not_awaited()
