from __future__ import annotations

import pytest

from app.models.asset import AssetType
from app.services import asset_seed_service


@pytest.mark.asyncio
async def test_seed_rejects_nontradable_brax_before_upsert(monkeypatch) -> None:
    async def fake_fetch_all_tickers_v2(subtype: str):
        if subtype == "stock":
            return [
                {"stock": "BRAX", "name": "BRAX"},
                {"stock": "PETR4", "name": "Petrobras"},
            ]
        return []

    upserts: list[tuple[str, AssetType]] = []

    async def fake_upsert_asset(db, ticker, name, asset_type, sector, logo_url=None):
        upserts.append((ticker, asset_type))
        return "created"

    class FakeDb:
        async def commit(self) -> None:
            return None

    monkeypatch.setattr(
        asset_seed_service,
        "fetch_all_tickers_v2",
        fake_fetch_all_tickers_v2,
    )
    monkeypatch.setattr(asset_seed_service, "_upsert_asset", fake_upsert_asset)

    result = await asset_seed_service.run_asset_seed(
        FakeDb(),
        include_crypto=False,
    )

    assert upserts == [("PETR4", AssetType.ACAO)]
    assert "BRAX" not in result.seeded_tickers[AssetType.ACAO.value]
    assert "PETR4" in result.seeded_tickers[AssetType.ACAO.value]
    assert result.created == 1
    assert result.skipped == 1
