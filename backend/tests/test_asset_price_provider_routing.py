from datetime import date

import pytest

from app.models.asset import AssetType
from app.services.asset_price_gap_sync_service import (
    MissingPriceRange,
    _fetch_range,
    normalize_provider_symbol,
)


def test_normaliza_simbolos_de_cripto_para_yahoo():
    assert normalize_provider_symbol("BITCOIN", AssetType.CRIPTO) == "BTC-USD"
    assert normalize_provider_symbol("ETHEREUM", AssetType.CRIPTO) == "ETH-USD"
    assert normalize_provider_symbol("CARDANO", AssetType.CRIPTO) == "ADA-USD"


def test_preserva_alias_fracionario_para_simbolo_base():
    assert normalize_provider_symbol("AHEB5F", AssetType.ACAO) == "AHEB5"
    assert normalize_provider_symbol("TRAD3F", AssetType.ACAO) == "TRAD3"


@pytest.mark.asyncio
async def test_brapi_vazia_nao_dispara_yahoo(monkeypatch):
    calls = {"brapi": 0, "yahoo": 0}

    async def fake_brapi(*args, **kwargs):
        calls["brapi"] += 1
        return []

    async def fake_yahoo(*args, **kwargs):
        calls["yahoo"] += 1
        return []

    monkeypatch.setattr("app.integrations.brapi.fetch_stocks_historical_v2", fake_brapi)
    monkeypatch.setattr("app.services.asset_price_gap_sync_service._fetch_yf_max", fake_yahoo)

    rows, source, status = await _fetch_range(
        "A1GT34",
        AssetType.BDR,
        MissingPriceRange(date(1900, 1, 1), date.today(), "missing_start"),
    )

    assert rows == []
    assert source == "brapi_v2_stocks_max"
    assert status == "HISTORY_START_EXHAUSTED"
    assert calls == {"brapi": 1, "yahoo": 0}
