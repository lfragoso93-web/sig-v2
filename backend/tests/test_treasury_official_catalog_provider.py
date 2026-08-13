from __future__ import annotations

import pytest

from app.integrations import treasury_catalog_provider as provider


def test_parse_official_catalog_csv_preserves_historical_families() -> None:
    csv_text = """Tipo Titulo;Data Vencimento;Data Base
Tesouro Selic;01/03/2029;08/08/2026
Tesouro Prefixado;01/01/2029;08/08/2026
Tesouro Prefixado com Juros Semestrais;01/01/2031;08/08/2026
Tesouro IPCA+;15/05/2035;08/08/2026
Tesouro IPCA+ com Juros Semestrais;15/08/2045;08/08/2026
Tesouro IGP-M+ com Juros Semestrais;01/01/2031;08/08/2026
Tesouro RendA+ Aposentadoria Extra;15/12/2049;08/08/2026
Tesouro Educa+;15/12/2034;08/08/2026
"""

    items = provider.parse_official_catalog_csv(csv_text)
    symbols = {item["symbol"] for item in items}

    assert symbols == {
        "tesouro-selic-01032029",
        "tesouro-prefixado-01012029",
        "tesouro-prefixado-com-juros-semestrais-01012031",
        "tesouro-ipca-15052035",
        "tesouro-ipca-com-juros-semestrais-15082045",
        "tesouro-igpm-com-juros-semestrais-01012031",
        "tesouro-renda-mais-2030",
        "tesouro-educa-mais-2030",
    }
    assert all(item["source"] == provider.OFFICIAL_SOURCE for item in items)


@pytest.mark.asyncio
async def test_official_catalog_prevents_brapi_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    official = [{"symbol": "tesouro-selic-01032029", "source": provider.OFFICIAL_SOURCE}]
    fallback_called = False

    async def fake_official(_client):
        return official

    async def fake_brapi(_client, indexer=None, coupon_type=None):
        nonlocal fallback_called
        fallback_called = True
        return [{"symbol": "tesouro-selic-01032031"}]

    monkeypatch.setattr(provider, "_fetch_official_catalog", fake_official)
    monkeypatch.setattr(provider, "_fetch_brapi_treasury_list", fake_brapi)

    assert await provider.fetch_treasury_catalog() == official
    assert fallback_called is False


@pytest.mark.asyncio
async def test_brapi_is_used_only_when_official_catalog_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_official(_client):
        return []

    async def fake_brapi(_client, indexer=None, coupon_type=None):
        return [{"symbol": "tesouro-selic-01032031"}]

    monkeypatch.setattr(provider, "_fetch_official_catalog", fake_official)
    monkeypatch.setattr(provider, "_fetch_brapi_treasury_list", fake_brapi)

    items = await provider.fetch_treasury_catalog()

    assert items == [{"symbol": "tesouro-selic-01032031", "source": provider.BRAPI_FALLBACK_SOURCE}]
