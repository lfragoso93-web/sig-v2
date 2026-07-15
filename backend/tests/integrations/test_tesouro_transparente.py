from datetime import date

from app.integrations.tesouro_transparente import parse_history_csv


def test_parse_history_csv_normalizes_treasury_families():
    csv_text = """Tipo Titulo;Data Vencimento;Data Base;PU Compra Manha
Tesouro Selic;01/03/2031;15/07/2026;15.247,81
Tesouro Prefixado;01/01/2029;15/07/2026;812,35
Tesouro Prefixado com Juros Semestrais;01/01/2031;15/07/2026;1.015,42
Tesouro IPCA+;15/05/2029;15/07/2026;3.982,10
Tesouro IPCA+ com Juros Semestrais;15/08/2032;15/07/2026;4.100,25
Tesouro RendA+ Aposentadoria Extra;15/12/2060;15/07/2026;1.245,60
Tesouro Educa+;15/12/2031;15/07/2026;1.105,70
"""

    parsed = parse_history_csv(
        csv_text,
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
    )

    assert set(parsed) == {
        "tesouro-selic-01032031",
        "tesouro-prefixado-01012029",
        "tesouro-prefixado-com-juros-semestrais-01012031",
        "tesouro-ipca-15052029",
        "tesouro-ipca-com-juros-semestrais-15082032",
        "tesouro-renda-mais-2060",
        "tesouro-educa-mais-2031",
    }
    assert parsed["tesouro-selic-01032031"][0][1] == 15247.81
    assert parsed["tesouro-renda-mais-2060"][0][1] == 1245.60


def test_parse_history_csv_filters_symbols_and_dates():
    csv_text = """Tipo Titulo;Data Vencimento;Data Base;PU Compra Manha
Tesouro Selic;01/03/2031;14/07/2026;15.240,00
Tesouro Selic;01/03/2031;15/07/2026;15.247,81
Tesouro RendA+ Aposentadoria Extra;15/12/2060;15/07/2026;1.245,60
"""

    parsed = parse_history_csv(
        csv_text,
        symbols=["tesouro-selic-01032031"],
        start_date=date(2026, 7, 15),
        end_date=date(2026, 7, 15),
    )

    assert list(parsed) == ["tesouro-selic-01032031"]
    assert len(parsed["tesouro-selic-01032031"]) == 1
    assert parsed["tesouro-selic-01032031"][0][1] == 15247.81
