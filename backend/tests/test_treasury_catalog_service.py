from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.asset import Asset
from app.services.treasury_catalog_service import (
    _name,
    format_friendly_treasury_title,
    seed_treasury_assets,
)


def test_format_friendly_treasury_title_renda_all_variants() -> None:
    # Commercial conversion years without date
    assert format_friendly_treasury_title("Tesouro RendA+ 2030") == "Tesouro Renda+ 2030"
    assert format_friendly_treasury_title("Tesouro RendA+ 2035") == "Tesouro Renda+ 2035"
    assert format_friendly_treasury_title("Tesouro RendA+ 2040") == "Tesouro Renda+ 2040"
    assert format_friendly_treasury_title("Tesouro RendA+ 2045") == "Tesouro Renda+ 2045"
    assert format_friendly_treasury_title("Tesouro RendA+ 2050") == "Tesouro Renda+ 2050"
    assert format_friendly_treasury_title("Tesouro RendA+ 2055") == "Tesouro Renda+ 2055"
    assert format_friendly_treasury_title("Tesouro RendA+ 2060") == "Tesouro Renda+ 2060"
    assert format_friendly_treasury_title("Tesouro RendA+ 2065") == "Tesouro Renda+ 2065"
    assert format_friendly_treasury_title("Tesouro RendA+ 2070") == "Tesouro Renda+ 2070"

    # With 'Aposentadoria Extra' subtitle
    assert (
        format_friendly_treasury_title("Tesouro RendA+ Aposentadoria Extra 2030")
        == "Tesouro Renda+ 2030"
    )
    assert (
        format_friendly_treasury_title("Tesouro RendA+ Aposentadoria Extra 2065")
        == "Tesouro Renda+ 2065"
    )

    # Full dates (financial maturity dates)
    assert (
        format_friendly_treasury_title("Tesouro RendA+ Aposentadoria Extra 15/12/2049")
        == "Tesouro Renda+ 2030"
    )
    assert (
        format_friendly_treasury_title("Tesouro RendA+ Aposentadoria Extra 15/12/2079")
        == "Tesouro Renda+ 2060"
    )
    assert (
        format_friendly_treasury_title("Tesouro RendA+ Aposentadoria Extra 15/12/2084")
        == "Tesouro Renda+ 2065"
    )
    assert (
        format_friendly_treasury_title("Tesouro RendA+ Aposentadoria Extra 15/12/2089")
        == "Tesouro Renda+ 2070"
    )

    # With ticker
    assert (
        format_friendly_treasury_title("Tesouro RendA+", "tesouro-renda-mais-2030")
        == "Tesouro Renda+ 2030"
    )
    assert (
        format_friendly_treasury_title("Tesouro RendA+ 2049", "tesouro-renda-mais-2030")
        == "Tesouro Renda+ 2030"
    )
    assert (
        format_friendly_treasury_title("Tesouro RendA+", "tesouro-renda-mais-2070")
        == "Tesouro Renda+ 2070"
    )


def test_format_friendly_treasury_title_educa_all_variants() -> None:
    # Commercial conversion years
    assert format_friendly_treasury_title("Tesouro Educa+ 2026") == "Tesouro Educa+ 2026"
    assert format_friendly_treasury_title("Tesouro Educa+ 2030") == "Tesouro Educa+ 2030"
    assert format_friendly_treasury_title("Tesouro Educa+ 2035") == "Tesouro Educa+ 2035"
    assert format_friendly_treasury_title("Tesouro Educa+ 2042") == "Tesouro Educa+ 2042"
    assert format_friendly_treasury_title("Tesouro Educa+ 2043") == "Tesouro Educa+ 2043"

    # Full dates (financial maturity dates)
    assert format_friendly_treasury_title("Tesouro Educa+ 15/12/2030") == "Tesouro Educa+ 2026"
    assert format_friendly_treasury_title("Tesouro Educa+ 15/12/2034") == "Tesouro Educa+ 2030"
    assert format_friendly_treasury_title("Tesouro Educa+ 15/12/2046") == "Tesouro Educa+ 2042"
    assert format_friendly_treasury_title("Tesouro Educa+ 15/12/2047") == "Tesouro Educa+ 2043"
    assert format_friendly_treasury_title("Tesouro Educa+ 2046") == "Tesouro Educa+ 2042"
    assert format_friendly_treasury_title("Tesouro Educa+ 2047") == "Tesouro Educa+ 2043"

    # With ticker
    assert (
        format_friendly_treasury_title("Tesouro Educa+", "tesouro-educa-mais-2026")
        == "Tesouro Educa+ 2026"
    )
    assert (
        format_friendly_treasury_title("Tesouro Educa+", "tesouro-educa-mais-2043")
        == "Tesouro Educa+ 2043"
    )
    # Ticker takes precedence when legacy name contained maturity year instead of commercial year
    assert (
        format_friendly_treasury_title("Tesouro Educa+ 2030", "tesouro-educa-mais-2026")
        == "Tesouro Educa+ 2026"
    )
    assert (
        format_friendly_treasury_title("Tesouro Renda+ 2049", "tesouro-renda-mais-2030")
        == "Tesouro Renda+ 2030"
    )


def test_format_friendly_treasury_title_traditional_bonds() -> None:
    assert (
        format_friendly_treasury_title("Tesouro Selic 2029 01/03/2029")
        == "Tesouro Selic 2029"
    )
    assert (
        format_friendly_treasury_title("Tesouro Selic", "tesouro-selic-01032029")
        == "Tesouro Selic 2029"
    )
    assert (
        format_friendly_treasury_title("Tesouro Prefixado", "tesouro-prefixado-01012029")
        == "Tesouro Prefixado 2029"
    )
    assert (
        format_friendly_treasury_title("Tesouro IPCA+", "tesouro-ipca-15082035")
        == "Tesouro IPCA+ 2035"
    )
    assert (
        format_friendly_treasury_title("Tesouro Prefixado 2028 01/01/2028")
        == "Tesouro Prefixado 2028"
    )
    assert (
        format_friendly_treasury_title("Tesouro IPCA+ com Juros Semestrais 2035 15/05/2035")
        == "Tesouro IPCA+ com Juros Semestrais 2035"
    )
    assert (
        format_friendly_treasury_title("Tesouro Prefixado 01/04/2006")
        == "Tesouro Prefixado 2006"
    )
    # Direct slug formatting without friendly name
    assert (
        format_friendly_treasury_title("tesouro-selic-01032029")
        == "Tesouro Selic 2029"
    )
    assert (
        format_friendly_treasury_title(None, "tesouro-selic-01032029")
        == "Tesouro Selic 2029"
    )
    assert (
        format_friendly_treasury_title("tesouro-prefixado-01012029")
        == "Tesouro Prefixado 2029"
    )
    assert (
        format_friendly_treasury_title("tesouro-prefixado-com-juros-semestrais-01012031")
        == "Tesouro Prefixado com Juros Semestrais 2031"
    )
    assert (
        format_friendly_treasury_title("tesouro-ipca-15082035")
        == "Tesouro IPCA+ 2035"
    )
    assert (
        format_friendly_treasury_title("tesouro-ipca-com-juros-semestrais-15082045")
        == "Tesouro IPCA+ com Juros Semestrais 2045"
    )
    assert (
        format_friendly_treasury_title("tesouro-igpm-com-juros-semestrais-01012031")
        == "Tesouro IGPM com Juros Semestrais 2031"
    )


def test_name_derivation_from_catalog_items() -> None:
    # RendA+ with maturity in 2049 should derive friendly commercial name 2030
    renda_item = {
        "bondType": "Tesouro RendA+ Aposentadoria Extra",
        "maturityDate": "2049-12-15",
        "maturityYear": 2049,
    }
    assert _name(renda_item, "tesouro-renda-mais-2030") == "Tesouro Renda+ 2030"

    # Educa+ with maturity in 2030 should derive friendly commercial name 2026
    educa_item = {
        "bondType": "Tesouro Educa+",
        "maturityDate": "2030-12-15",
        "maturityYear": 2030,
    }
    assert _name(educa_item, "tesouro-educa-mais-2026") == "Tesouro Educa+ 2026"

    # Selic traditional bond retains maturity year in name
    selic_item = {
        "bondType": "Tesouro Selic",
        "maturityDate": "2029-03-01",
        "maturityYear": 2029,
    }
    assert _name(selic_item, "tesouro-selic-01032029") == "Tesouro Selic 2029"


@pytest.mark.asyncio
async def test_seed_treasury_assets_creates_and_updates_with_friendly_names(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_items = [
        {
            "symbol": "tesouro-renda-mais-2030",
            "bondType": "Tesouro RendA+ Aposentadoria Extra",
            "maturityDate": "2049-12-15",
            "maturityYear": 2049,
            "indexer": "IPCA",
            "source": "tesouro_transparente_csv",
        },
        {
            "symbol": "tesouro-educa-mais-2026",
            "bondType": "Tesouro Educa+",
            "maturityDate": "2030-12-15",
            "maturityYear": 2030,
            "indexer": "IPCA",
            "source": "tesouro_transparente_csv",
        },
    ]

    import app.services.treasury_catalog_service as tcs
    monkeypatch.setattr(tcs, "fetch_treasury_catalog", AsyncMock(return_value=catalog_items))
    monkeypatch.setattr(
        tcs,
        "consolidate_legacy_educa_identities",
        AsyncMock(return_value=SimpleNamespace(consolidated=0, errors=0)),
    )

    # First run: empty database -> creates assets with friendly commercial names
    db = MagicMock()
    added_assets: list[Asset] = []
    db.add.side_effect = lambda a: added_assets.append(a)
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    class _EmptyResult:
        def scalar_one_or_none(self):
            return None

    db.execute = AsyncMock(return_value=_EmptyResult())

    result = await seed_treasury_assets(db, commit=True)

    assert result.created == 2
    assert result.errors == 0
    assert len(added_assets) == 2
    names_by_ticker = {str(a.ticker): str(a.name) for a in added_assets}
    assert names_by_ticker["tesouro-renda-mais-2030"] == "Tesouro Renda+ 2030"
    assert names_by_ticker["tesouro-educa-mais-2026"] == "Tesouro Educa+ 2026"
