from app.integrations.brapi_treasury import (
    _SYNTHETIC_LONG_TERM_BONDS,
    _parse_tesouro_csv,
    canonical_treasury_symbol_from_text,
)


def test_canonical_treasury_symbol_renda_commercial_and_maturity_variants() -> None:
    # Commercial conversion years
    assert (
        canonical_treasury_symbol_from_text("Tesouro RendA+ 2030")
        == "tesouro-renda-mais-2030"
    )
    assert (
        canonical_treasury_symbol_from_text("TESOURO RENDA+ APOSENTADORIA EXTRA 2030")
        == "tesouro-renda-mais-2030"
    )
    assert (
        canonical_treasury_symbol_from_text("TESOURO RENDA+ 2065")
        == "tesouro-renda-mais-2065"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Renda+ 2050")
        == "tesouro-renda-mais-2050"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro RendA+ 2070")
        == "tesouro-renda-mais-2070"
    )

    # Full dates (financial maturity dates)
    assert (
        canonical_treasury_symbol_from_text(
            "Tesouro RendA+ Aposentadoria Extra 15/12/2049"
        )
        == "tesouro-renda-mais-2030"
    )
    assert (
        canonical_treasury_symbol_from_text(
            "Tesouro RendA+ Aposentadoria Extra 15/12/2084"
        )
        == "tesouro-renda-mais-2065"
    )
    assert (
        canonical_treasury_symbol_from_text(
            "Tesouro RendA+ Aposentadoria Extra 15/12/2089"
        )
        == "tesouro-renda-mais-2070"
    )
    assert (
        canonical_treasury_symbol_from_text(
            "Tesouro RendA+ 2049-12-15"
        )
        == "tesouro-renda-mais-2030"
    )

    # Legacy maturity symbol resolution
    assert (
        canonical_treasury_symbol_from_text("tesouro-renda-mais-2049")
        == "tesouro-renda-mais-2030"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-renda-mais-2084")
        == "tesouro-renda-mais-2065"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-renda-mais-2070")
        == "tesouro-renda-mais-2070"
    )


def test_canonical_treasury_symbol_educa_commercial_and_maturity_variants() -> None:
    # Commercial conversion years
    assert (
        canonical_treasury_symbol_from_text("TESOURO EDUCA+ 2026")
        == "tesouro-educa-mais-2026"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 2030")
        == "tesouro-educa-mais-2030"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 2042")
        == "tesouro-educa-mais-2042"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 2043")
        == "tesouro-educa-mais-2043"
    )

    # Full dates (financial maturity dates)
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 15/12/2030")
        == "tesouro-educa-mais-2026"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 15/12/2034")
        == "tesouro-educa-mais-2030"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 15/12/2046")
        == "tesouro-educa-mais-2042"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 15/12/2047")
        == "tesouro-educa-mais-2043"
    )

    # Legacy symbols with 8-digit maturity date
    assert (
        canonical_treasury_symbol_from_text("tesouro-educa-15122030")
        == "tesouro-educa-mais-2026"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-educa-15122031")
        == "tesouro-educa-mais-2027"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-educa-mais-2043")
        == "tesouro-educa-mais-2043"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 2046")
        == "tesouro-educa-mais-2042"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-educa-mais-2046")
        == "tesouro-educa-mais-2042"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Educa+ 2047")
        == "tesouro-educa-mais-2043"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-educa-mais-2047")
        == "tesouro-educa-mais-2043"
    )


def test_canonical_treasury_symbol_traditional_bonds() -> None:
    assert (
        canonical_treasury_symbol_from_text("TESOURO SELIC 2031")
        == "tesouro-selic-01032031"
    )
    assert (
        canonical_treasury_symbol_from_text("TESOURO PREFIXADO 2028")
        == "tesouro-prefixado-01012028"
    )
    assert (
        canonical_treasury_symbol_from_text("TESOURO IPCA+ 2035")
        == "tesouro-ipca-15082035"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-prefixado-01042006")
        == "tesouro-prefixado-01042006"
    )
    assert (
        canonical_treasury_symbol_from_text("tesouro-ipca-15052029")
        == "tesouro-ipca-15052029"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro IPCA+ 15/05/2029")
        == "tesouro-ipca-15052029"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro Prefixado 01/04/2006")
        == "tesouro-prefixado-01042006"
    )
    assert (
        canonical_treasury_symbol_from_text("Tesouro IGPM com Juros Semestrais 01/01/2031")
        == "tesouro-igpm-com-juros-semestrais-01012031"
    )


def test_synthetic_long_term_bonds_separation_of_name_and_maturity() -> None:
    renda_bonds = [
        b for b in _SYNTHETIC_LONG_TERM_BONDS
        if b["symbol"].startswith("tesouro-renda-mais-")
    ]
    assert len(renda_bonds) > 0

    for bond in renda_bonds:
        # e.g. tesouro-renda-mais-2030 -> conversion year 2030
        conversion_year = int(bond["symbol"].replace("tesouro-renda-mais-", ""))
        assert str(conversion_year) in bond["name"]
        assert bond["maturityYear"] == conversion_year + 19
        assert bond["maturityDate"] == f"{conversion_year + 19}-12-15"
        assert bond["couponType"] == "monthly_income"

    assert any(b["symbol"] == "tesouro-renda-mais-2070" for b in renda_bonds)

    educa_bonds = [
        b for b in _SYNTHETIC_LONG_TERM_BONDS
        if b["symbol"].startswith("tesouro-educa-mais-")
    ]
    assert len(educa_bonds) > 0
    assert any(b["symbol"] == "tesouro-educa-mais-2043" for b in educa_bonds)

    for bond in educa_bonds:
        # e.g. tesouro-educa-mais-2026 -> conversion year 2026
        conversion_year = int(bond["symbol"].replace("tesouro-educa-mais-", ""))
        assert str(conversion_year) in bond["name"]
        assert bond["maturityYear"] == conversion_year + 4
        assert bond["maturityDate"] == f"{conversion_year + 4}-12-15"
        assert bond["couponType"] == "monthly_income"


def test_parse_tesouro_csv_preserves_commercial_name_and_maturity() -> None:
    csv_text = """Tipo Titulo;Data Vencimento;PU Compra Manha
Tesouro RendA+ Aposentadoria Extra;15/12/2049;1.200,00
Tesouro RendA+ 2049;15/12/2049;1.200,00
Tesouro Educa+;15/12/2030;1.100,00
Tesouro Selic;01/03/2029;14.000,00
Tesouro Selic 2029;01/03/2029;14.000,00
Tesouro IPCA+;15/05/2029;3.500,00
"""
    items = _parse_tesouro_csv(csv_text)
    items_by_symbol = {item["symbol"]: item for item in items}

    assert "tesouro-renda-mais-2030" in items_by_symbol
    renda = items_by_symbol["tesouro-renda-mais-2030"]
    assert "2030" in renda["name"]
    assert "2049" not in renda["name"]
    assert renda["maturityDate"] == "15/12/2049"

    assert "tesouro-educa-mais-2026" in items_by_symbol
    educa = items_by_symbol["tesouro-educa-mais-2026"]
    assert "2026" in educa["name"]
    assert educa["maturityDate"] == "15/12/2030"

    assert "tesouro-selic-01032029" in items_by_symbol
    selic = items_by_symbol["tesouro-selic-01032029"]
    assert selic["maturityDate"] == "01/03/2029"
    assert selic["name"] == "Tesouro Selic 2029"
    assert "2029 2029" not in selic["name"]

    assert "tesouro-ipca-15052029" in items_by_symbol
    ipca = items_by_symbol["tesouro-ipca-15052029"]
    assert ipca["maturityDate"] == "15/05/2029"


def test_normalize_treasury_ticker_in_brapi() -> None:
    from app.integrations.brapi import _normalize_treasury_ticker

    assert _normalize_treasury_ticker("TESOURO EDUCA+ 2035") == "tesouro-educa-mais-2035"
    assert _normalize_treasury_ticker("TESOURO EDUCA+ 2026") == "tesouro-educa-mais-2026"
    assert _normalize_treasury_ticker("TESOURO RENDA+ 2070") == "tesouro-renda-mais-2070"
    assert _normalize_treasury_ticker("Tesouro Selic 2029") == "tesouro-selic-01032029"
