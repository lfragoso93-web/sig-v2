import asyncio
from datetime import date

from app.integrations import tesouro_transparente_prices as prices_module
from app.integrations.tesouro_transparente_prices import _parse_latest_prices


def test_parse_latest_prices_uses_commercial_year_for_renda_mais():
    csv_text = """Tipo Titulo;Data Vencimento;Data Base;PU Compra Manha
Tesouro RendA+ Aposentadoria Extra;15/12/2079;15/07/2026;1.245,60
Tesouro RendA+ Aposentadoria Extra;15/12/2084;15/07/2026;1.110,25
"""

    prices = _parse_latest_prices(
        csv_text,
        {"tesouro-renda-mais-2060", "tesouro-renda-mais-2065"},
    )

    assert prices == {
        "tesouro-renda-mais-2060": (date(2026, 7, 15), 1245.60),
        "tesouro-renda-mais-2065": (date(2026, 7, 15), 1110.25),
    }


def test_parse_latest_prices_keeps_latest_row_for_symbol():
    csv_text = """Tipo Titulo;Data Vencimento;Data Base;PU Compra Manha
Tesouro RendA+ Aposentadoria Extra;15/12/2084;14/07/2026;1.100,00
Tesouro RendA+ Aposentadoria Extra;15/12/2084;15/07/2026;1.110,25
"""

    prices = _parse_latest_prices(csv_text, {"tesouro-renda-mais-2065"})

    assert prices["tesouro-renda-mais-2065"] == (
        date(2026, 7, 15),
        1110.25,
    )


def test_parse_latest_prices_accepts_bom_and_spaces_in_headers():
    csv_text = """\ufeff Tipo Titulo ; Data Vencimento ; Data Base ; PU Compra Manha 
Tesouro RendA+ Aposentadoria Extra;15/12/2084;15/07/2026;1.110,25
"""

    prices = _parse_latest_prices(csv_text, {"tesouro-renda-mais-2065"})

    assert prices["tesouro-renda-mais-2065"] == (
        date(2026, 7, 15),
        1110.25,
    )


def test_fetch_prices_scans_resources_beyond_first_five(monkeypatch):
    urls = [f"https://example.test/resource-{index}.csv" for index in range(6)]
    empty_csv = "Tipo Titulo;Data Vencimento;Data Base;PU Compra Manha\n"
    target_csv = """Tipo Titulo;Data Vencimento;Data Base;PU Compra Manha
Tesouro RendA+ Aposentadoria Extra;15/12/2084;15/07/2026;1.110,25
"""

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, **kwargs):
            return FakeResponse(target_csv if url == urls[-1] else empty_csv)

    async def fake_discover_csv_resources(client):
        return urls

    monkeypatch.setattr(prices_module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(
        prices_module,
        "discover_csv_resources",
        fake_discover_csv_resources,
    )

    prices = asyncio.run(
        prices_module.fetch_tesouro_transparente_prices(
            ["tesouro-renda-mais-2065"]
        )
    )

    assert prices == {"tesouro-renda-mais-2065": 1110.25}
