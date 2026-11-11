"""Testes para o adapter de Notas de Corretagem padrão Sinacor."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.brokerage_note_adapter_service import (
    adapt_brokerage_note_pdf_to_canonical,
    adapt_brokerage_note_text_to_canonical,
    is_brokerage_note_content,
)


def test_sinacor_detection_positive_and_negative():
    valid_text = (
        "NOTA DE NEGOCIAÇÃO\n"
        "Nr. nota: 987654\n"
        "Data pregão: 10/03/2024\n"
        "1-BOVESPA C VISTA WEGE3 ON NM 100 35,00 3.500,00 D\n"
    )
    assert is_brokerage_note_content(valid_text) is True

    invalid_text = "Algum outro documento financeiro sem termos de corretagem."
    assert is_brokerage_note_content(invalid_text) is False


def test_adapt_sinacor_text_multi_asset_proportional_fees():
    note_text = (
        "NOTA DE NEGOCIAÇÃO Nº 10001\n"
        "Folha: 1\n"
        "Data pregão: 15/01/2024\n"
        "XP INVESTIMENTOS CCTVM S/A\n"
        "Q Negociação C/V Tipo mercado Prazo Especificação do título Obs. (*) Quantidade Preço / Ajuste Valor Operação / Ajuste D/C\n"
        "1-BOVESPA C VISTA WEGE3 ON NM 100 35,50 3.550,00 D\n"
        "1-BOVESPA C VISTA CXSE3 ON NM 200 12,00 2.400,00 D\n"
        "Resumo dos Negócios\n"
        "Total custos / despesas 0,30 C\n"
    )

    result = adapt_brokerage_note_text_to_canonical(note_text)
    assert result.success is True
    assert result.format_detected == "sinacor_brokerage_note_v1"
    assert len(result.canonical_rows) == 2

    wege_row = result.canonical_rows[0]
    assert wege_row["ticker"] == "WEGE3"
    assert wege_row["operation"] == "buy"
    assert wege_row["quantity"] == "100"
    assert wege_row["price"] == "35.50"
    assert wege_row["date"] == "2024-01-15"
    assert Decimal(wege_row["fees"]) > Decimal("0")

    cxse_row = result.canonical_rows[1]
    assert cxse_row["ticker"] == "CXSE3"
    assert cxse_row["operation"] == "buy"
    assert cxse_row["quantity"] == "200"
    assert cxse_row["price"] == "12.00"
    assert cxse_row["date"] == "2024-01-15"
    assert Decimal(cxse_row["fees"]) > Decimal("0")

    total_fees = Decimal(wege_row["fees"]) + Decimal(cxse_row["fees"])
    assert total_fees == Decimal("0.30")


def test_adapt_sinacor_fracionario_and_sell():
    note_text = (
        "NOTA DE CORRETAGEM\n"
        "Data pregão: 22/02/2024\n"
        "BANCO INTER DTVM LTDA\n"
        "1-BOVESPA V FRACIONARIO PETR4F ON NM 15 40,00 600,00 C\n"
        "Taxa de liquidação 0,15\n"
        "Emolumentos 0,05\n"
    )

    result = adapt_brokerage_note_text_to_canonical(note_text)
    assert result.success is True
    assert len(result.canonical_rows) == 1

    petr4_row = result.canonical_rows[0]
    # PETR4F deve ter o sufixo F removido para normalização do ticker canônico
    assert petr4_row["ticker"] == "PETR4"
    assert petr4_row["operation"] == "sell"
    assert petr4_row["quantity"] == "15"
    assert petr4_row["price"] == "40.00"
    assert petr4_row["date"] == "2024-02-22"
    assert Decimal(petr4_row["fees"]) == Decimal("0.20")
    assert "Banco Inter" in petr4_row["notes"] or "INTER" in petr4_row["notes"]


def test_adapt_brokerage_note_pdf_delegates_to_text_parser():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "NOTA DE NEGOCIAÇÃO\n"
        "Data pregão: 05/04/2024\n"
        "CLEAR CORRETORA\n"
        "1-BOVESPA C VISTA VALE3 ON NM 100 65,00 6.500,00 D\n"
        "Total custos / despesas 1,50\n"
    )

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = adapt_brokerage_note_pdf_to_canonical(b"%PDF-fake-note")

    assert result.success is True
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "VALE3"
    assert result.canonical_rows[0]["operation"] == "buy"
    assert result.canonical_rows[0]["quantity"] == "100"
    assert result.canonical_rows[0]["price"] == "65.00"
    assert result.canonical_rows[0]["date"] == "2024-04-05"
    assert Decimal(result.canonical_rows[0]["fees"]) == Decimal("1.50")


def test_adapt_sinacor_fee_rounding_reconciliation_exact_sum():
    # 3 operações de mesmo volume com total de custos de 0,01 centavo
    note_text = (
        "NOTA DE NEGOCIAÇÃO\n"
        "Data pregão: 10/01/2024\n"
        "XP INVESTIMENTOS\n"
        "1-BOVESPA C VISTA WEGE3 ON NM 10 10,00 100,00 D\n"
        "1-BOVESPA C VISTA PETR4 ON NM 10 10,00 100,00 D\n"
        "1-BOVESPA C VISTA VALE3 ON NM 10 10,00 100,00 D\n"
        "Total custos / despesas 0,01\n"
    )
    result = adapt_brokerage_note_text_to_canonical(note_text)
    assert result.success is True
    assert len(result.canonical_rows) == 3
    sum_fees = sum(Decimal(r["fees"]) for r in result.canonical_rows)
    assert sum_fees == Decimal("0.01")


def test_adapt_sinacor_handles_pathological_whitespace_linearly():
    import time

    tab_flood = "C" + ("\t" * 5000) + "WEGE3" + ("\t,\t," * 1000)
    note_text = (
        "NOTA DE NEGOCIAÇÃO\n"
        "Data pregão: 10/01/2024\n"
        f"{tab_flood}\n"
        "C WEGE3 ON 10 35,00\n"
    )
    started = time.monotonic()
    result = adapt_brokerage_note_text_to_canonical(note_text)
    elapsed = time.monotonic() - started
    assert elapsed < 1.0
    assert result.success is True
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "WEGE3"


def test_adapt_sinacor_attached_dc_and_wrapped_multiline_columns():
    note_text = (
        "NOTA DE NEGOCIAÇÃO\n"
        "Data pregão: 18/03/2024\n"
        "XP INVESTIMENTOS\n"
        "1-BOVESPAC VISTA WEGE3 ON NM 100 35,00 3.500,00D\n"
        "1-BOVESPA V VISTA PETR4 ON NM\n"
        "50 40,00 2.000,00 C\n"
        "Total custos / despesas 0,55\n"
    )
    result = adapt_brokerage_note_text_to_canonical(note_text)
    assert result.success is True
    assert len(result.canonical_rows) == 2

    assert result.canonical_rows[0]["ticker"] == "WEGE3"
    assert result.canonical_rows[0]["operation"] == "buy"
    assert result.canonical_rows[0]["quantity"] == "100"
    assert result.canonical_rows[0]["price"] == "35.00"

    assert result.canonical_rows[1]["ticker"] == "PETR4"
    assert result.canonical_rows[1]["operation"] == "sell"
    assert result.canonical_rows[1]["quantity"] == "50"
    assert result.canonical_rows[1]["price"] == "40.00"

    sum_fees = sum(Decimal(r["fees"]) for r in result.canonical_rows)
    assert sum_fees == Decimal("0.55")
