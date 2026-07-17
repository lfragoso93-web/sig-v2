from types import SimpleNamespace

import pytest

from app.models.asset import Asset, AssetType
from app.services import treasury_catalog_v2_service as service


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, assets):
        self.assets = assets
        self.added = []
        self.commits = 0

    async def execute(self, _statement):
        return _ScalarResult(self.assets)

    def add(self, asset):
        self.added.append(asset)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1


def _asset(ticker: str, *, status: str = "OK") -> Asset:
    return Asset(
        id=1,
        ticker=ticker,
        name="Tesouro RendA+ Aposentadoria Extra 15/12/2084",
        asset_type=AssetType.TESOURO_DIRETO.value,
        currency="BRL",
        sector="Tesouro Direto",
        provider="tesouro_transparente",
        provider_symbol=ticker,
        provider_status=status,
    )


@pytest.mark.asyncio
async def test_sync_reuses_case_variant_without_creating_duplicate(monkeypatch):
    existing = _asset("TESOURO-RENDA-MAIS-2065")
    db = _FakeSession([existing])
    fetched = service.OfficialTreasuryCatalogFetch(
        catalog={
            "tesouro-renda-mais-2065": {
                "symbol": "tesouro-renda-mais-2065",
                "legacy_maturity_symbol": "tesouro-renda-mais-2084",
                "name": "Tesouro RendA+ Aposentadoria Extra 15/12/2084",
                "title": "Tesouro RendA+ Aposentadoria Extra",
                "maturity": "15/12/2084",
            }
        },
        resources=2,
        errors=0,
    )

    async def fake_fetch():
        return fetched

    monkeypatch.setattr(service, "_fetch_official_treasury_catalog_status", fake_fetch)

    result = await service.sync_treasury_catalog_v2(db)

    assert result.created == 0
    assert result.updated == 1
    assert existing.id == 1
    assert existing.ticker == "tesouro-renda-mais-2065"
    assert db.added == []
    assert db.commits == 1


@pytest.mark.asyncio
async def test_partial_catalog_does_not_mark_missing_asset_inactive(monkeypatch):
    existing = _asset("tesouro-renda-mais-2060", status="OK")
    db = _FakeSession([existing])
    fetched = service.OfficialTreasuryCatalogFetch(
        catalog={
            "tesouro-renda-mais-2065": {
                "symbol": "tesouro-renda-mais-2065",
                "legacy_maturity_symbol": "tesouro-renda-mais-2084",
                "name": "Tesouro RendA+ Aposentadoria Extra 15/12/2084",
                "title": "Tesouro RendA+ Aposentadoria Extra",
                "maturity": "15/12/2084",
            }
        },
        resources=2,
        errors=1,
    )

    async def fake_fetch():
        return fetched

    monkeypatch.setattr(service, "_fetch_official_treasury_catalog_status", fake_fetch)

    result = await service.sync_treasury_catalog_v2(db)

    assert result.errors == 1
    assert result.review_marked == 0
    assert existing.provider_status == "OK"
    assert existing.provider_last_error is None
