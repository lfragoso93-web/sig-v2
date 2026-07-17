from datetime import date

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
