"""Testes para o adapter da Área do Investidor B3 (Issue #358)."""
import io
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import openpyxl
import pytest
from app.models.asset import AssetType
from app.services.b3_investor_area_adapter_service import (
    adapt_b3_investor_csv_to_canonical,
    adapt_b3_investor_pdf_to_canonical,
    adapt_b3_investor_xlsx_to_canonical,
    infer_b3_asset_type,
    is_b3_csv_content,
    normalize_b3_ticker,
    parse_b3_date,
    parse_b3_number,
)
from app.services.csv_import_service import import_transactions_csv
from sqlalchemy.ext.asyncio import AsyncSession


class FakeUpload:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self) -> bytes:
        return self._content


def test_normalize_b3_ticker_odd_lot_and_description():
    assert normalize_b3_ticker("PETR4F") == "PETR4"
    assert normalize_b3_ticker("VALE3") == "VALE3"
    assert normalize_b3_ticker("HGLG11") == "HGLG11"
    assert normalize_b3_ticker("B3SA3 - B3 S.A. BRASIL BOLSA BALCAO") == "B3SA3"
    assert normalize_b3_ticker("TESOURO SELIC 2029 - NTN-B") == "TESOURO SELIC 2029"


def test_infer_b3_asset_type():
    assert infer_b3_asset_type("PETR4") == AssetType.ACAO.value
    assert infer_b3_asset_type("HGLG11") == AssetType.FII.value
    assert infer_b3_asset_type("AAPL34") == AssetType.BDR.value
    assert infer_b3_asset_type("TESOURO SELIC 2029") == AssetType.TESOURO_DIRETO.value


def test_parse_b3_number_and_date():
    assert parse_b3_number("1.234,56") == Decimal("1234.56")
    assert parse_b3_number("R$ 35,50") == Decimal("35.50")
    assert parse_b3_number("-") == Decimal("0")
    assert parse_b3_date("15/01/2024") == "2024-01-15"
    assert parse_b3_date("2024-05-20") == "2024-05-20"


def test_adapt_b3_negociacao_file():
    raw_csv = (
        "Data do Negócio;Tipo de Movimentação;Mercado;Prazo/Vencimento;Instituição;Código de Negociação;Quantidade;Preço;Valor\n"
        "15/01/2024;Compra;Mercado à Vista;;XP INVESTIMENTOS;PETR4F;10;35,50;355,00\n"
        "20/01/2024;Venda;Mercado à Vista;;CLEAR CORRETORA;VALE3;100;70,00;7000,00\n"
    )
    assert is_b3_csv_content(raw_csv) is True
    result = adapt_b3_investor_csv_to_canonical(raw_csv)

    assert result.success is True
    assert result.format_detected == "b3_negociacao_v1"
    assert len(result.canonical_rows) == 2

    petr4_row = result.canonical_rows[0]
    assert petr4_row["ticker"] == "PETR4"
    assert petr4_row["operation"] == "buy"
    assert petr4_row["quantity"] == "10"
    assert petr4_row["price"] == "35.50"
    assert petr4_row["date"] == "2024-01-15"
    assert "XP INVESTIMENTOS" in petr4_row["notes"]

    vale3_row = result.canonical_rows[1]
    assert vale3_row["ticker"] == "VALE3"
    assert vale3_row["operation"] == "sell"
    assert vale3_row["quantity"] == "100"
    assert vale3_row["price"] == "70.00"
    assert vale3_row["date"] == "2024-01-20"


def test_adapt_b3_movimentacao_segregates_corporate_events():
    raw_csv = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;10/02/2024;Transferência - Liquidação;HGLG11 - CSHG LOGISTICA FII;XP INVESTIMENTOS;50;160,00;8000,00\n"
        "Credito;15/02/2024;Rendimento;HGLG11 - CSHG LOGISTICA FII;XP INVESTIMENTOS;50;1,10;55,00\n"
        "Credito;20/02/2024;Dividendo;PETR4 - PETROLEO BRASILEIRO S.A.;XP INVESTIMENTOS;100;2,50;250,00\n"
        "Credito;25/02/2024;Juros Sobre Capital Próprio;BBDC4 - BANCO BRADESCO S.A.;XP INVESTIMENTOS;200;0,20;40,00\n"
    )
    assert is_b3_csv_content(raw_csv) is True
    result = adapt_b3_investor_csv_to_canonical(raw_csv)

    assert result.success is True
    assert result.format_detected == "b3_movimentacao_v1"

    # Apenas a transferência/compra vira transação
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "HGLG11"
    assert result.canonical_rows[0]["operation"] == "buy"
    assert result.canonical_rows[0]["quantity"] == "50"
    assert result.canonical_rows[0]["price"] == "160.00"

    # Rendimento, Dividendo e JCP devem ter sido segregados como proventos
    assert len(result.skipped_items) == 3
    skipped_types = {item.movement_type for item in result.skipped_items}
    assert "Rendimento" in skipped_types
    assert "Dividendo" in skipped_types
    assert "Juros Sobre Capital Próprio" in skipped_types


@pytest.mark.asyncio
async def test_import_transactions_csv_with_b3_file_in_dry_run():
    db = AsyncMock(spec=AsyncSession)
    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = SimpleNamespace(id=1, user_id=7)
    duplicate_result = MagicMock()
    duplicate_result.scalar_one_or_none.return_value = None
    coverage_result = MagicMock()
    coverage_result.all.return_value = [
        SimpleNamespace(
            ticker="PETR4",
            asset_type="ACAO",
            last_price=35.5,
            price_rows=1,
        )
    ]
    db.execute.side_effect = [portfolio_result, duplicate_result, coverage_result]

    b3_bytes = (
        "Data do Negócio;Tipo de Movimentação;Mercado;Prazo/Vencimento;Instituição;Código de Negociação;Quantidade;Preço;Valor\n"
        "15/01/2024;Compra;Mercado à Vista;;XP INVESTIMENTOS;PETR4F;10;35,50;355,00\n"
    ).encode("latin-1")

    res = await import_transactions_csv(
        db=db,
        portfolio_id=1,
        user_id=7,
        file=FakeUpload(b3_bytes),
        dry_run=True,
        source="auto",
    )

    assert res["success"] is True
    assert res["adapter_format"] == "b3_negociacao_v1"
    assert len(res["rows"]) == 1
    assert res["rows"][0]["ticker"] == "PETR4"
    assert res["rows"][0]["operation"] == "buy"
    assert res["rows"][0]["quantity"] == 10.0


def test_adapt_b3_movimentacao_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Entrada/Saída", "Data", "Movimentação", "Produto", "Instituição", "Quantidade", "Preço unitário", "Valor da Operação"])
    ws.append(["Credito", "10/02/2024", "Transferência - Liquidação", "WEGE3 - WEG S.A.", "XP INVESTIMENTOS", 100, 35.50, 3550.00])
    ws.append(["Debito", "12/02/2024", "Transferência - Liquidação", "VALE3 - VALE S.A.", "XP INVESTIMENTOS", 50, 70.00, 3500.00])
    ws.append(["Credito", "15/02/2024", "Dividendo", "WEGE3 - WEG S.A.", "XP INVESTIMENTOS", 100, 0.50, 50.00])
    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    result = adapt_b3_investor_xlsx_to_canonical(xlsx_bytes)

    assert result.success is True
    assert result.format_detected == "b3_movimentacao_xlsx_v1"
    assert len(result.canonical_rows) == 2

    wege_row = result.canonical_rows[0]
    assert wege_row["ticker"] == "WEGE3"
    assert wege_row["operation"] == "buy"
    assert wege_row["quantity"] == "100"
    assert Decimal(wege_row["price"]) == Decimal("35.50")
    assert wege_row["date"] == "2024-02-10"

    vale_row = result.canonical_rows[1]
    assert vale_row["ticker"] == "VALE3"
    assert vale_row["operation"] == "sell"
    assert vale_row["quantity"] == "50"
    assert Decimal(vale_row["price"]) == Decimal("70.00")
    assert vale_row["date"] == "2024-02-12"

    assert len(result.skipped_items) == 1
    assert result.skipped_items[0].movement_type == "Dividendo"


def test_adapt_b3_movimentacao_pdf():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Área do Investidor - Extrato de Movimentação\n"
        "10 de Fevereiro de 2024\n"
        "Credito Transferência - Liquidação WEGE3 - WEG S.A. XP INVESTIMENTOS 100 35,50 3.550,00\n"
        "15 de Fevereiro de 2024\n"
        "Credito Rendimento HGLG11 - CSHG LOGISTICA FII XP INVESTIMENTOS 50 1,10 55,00\n"
    )
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = adapt_b3_investor_pdf_to_canonical(b"%PDF-fake-b3")

    assert result.success is True
    assert result.format_detected == "b3_movimentacao_pdf_v1"
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "WEGE3"
    assert result.canonical_rows[0]["operation"] == "buy"
    assert result.canonical_rows[0]["quantity"] == "100"
    assert result.canonical_rows[0]["price"] == "35.50"
    assert result.canonical_rows[0]["date"] == "2024-02-10"
    assert len(result.skipped_items) == 1
    assert result.skipped_items[0].movement_type == "Rendimento"


def test_infer_b3_asset_type_smart_etf_and_units():
    # ETFs terminados em 11
    assert infer_b3_asset_type("DIVD11", "DIVD11 - IT NOW IDIV RENDA DIV FDO DE ÍNDICE – RESP LIMIT") == AssetType.ETF_NACIONAL.value
    assert infer_b3_asset_type("AURO11", "AURO11 - BUENA VISTA NEOS GOLD HIGH INCOME INDEX FUNDO DE ÍNDICE") == AssetType.ETF_NACIONAL.value
    assert infer_b3_asset_type("COIN11", "COIN11 - BUENA VISTA N. BITCOIN H. I. INDEX FDO DE INDICE") == AssetType.ETF_NACIONAL.value
    assert infer_b3_asset_type("BOVA11") == AssetType.ETF_NACIONAL.value
    assert infer_b3_asset_type("SMAL11") == AssetType.ETF_NACIONAL.value

    # Units de Ações terminadas em 11
    assert infer_b3_asset_type("TAEE11", "TAEE11 - TRANSMISSORA ALIANCA DE ENERGIA ELETRICA S/A") == AssetType.ACAO.value
    assert infer_b3_asset_type("SANB11", "SANB11 - BANCO SANTANDER (BRASIL) S.A.") == AssetType.ACAO.value
    assert infer_b3_asset_type("KLBN11", "KLBN11 - KLABIN S/A") == AssetType.ACAO.value
    assert infer_b3_asset_type("ALUP11", "ALUP11 - ALUPAR INVESTIMENTO S/A") == AssetType.ACAO.value

    # FIIs e FIAGROs terminados em 11
    assert infer_b3_asset_type("HGLG11", "HGLG11 - CSHG LOGISTICA FDO INV IMOB - FII") == AssetType.FII.value
    assert infer_b3_asset_type("MXRF11", "MXRF11 - MAXI RENDA FDO INV IMOB - FII") == AssetType.FII.value
    assert infer_b3_asset_type("VGIA11", "VGIA11 - VALORA CRA FDO INV NAS CAD PROD AGRO FIAGRO - IMOB") == AssetType.FII.value
    assert infer_b3_asset_type("VCRA11", "VCRA11 - VECTIS DATAGRO CR AGR - FDO INV CAD PROD AG - IMOB") == AssetType.FII.value


def test_adapt_b3_movimentacao_pdf_multiline_wrapping():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "LEONARDO | CPF/CNPJ: 12345678900\n"
        "Filtros aplicados\n"
        "Data Inicial: 01/10/2024 | Data Final: 06/11/2026\n"
        "06 de novembro de 2026\n"
        "Movimentação Produto Instituição Quantidade Preço Unitário Valor da Operação\n"
        "Transferência -\n"
        "Liquidação\n"
        "GGRC11 - GGR COVEPI RENDA FDO\n"
        "INV IMOB RESPONSAB LTDA\n"
        "INTER DISTRIBUIDORA DE TITULOS\n"
        "E VALORES MOBILIARIOS LTDA 10 R$ 8,19 R$ 81,90\n"
        "Transferência -\n"
        "Liquidação\n"
        "DIVD11 - IT NOW IDIV RENDA DIV FDO DE ÍNDICE\n"
        "INTER DISTRIBUIDORA DE TITULOS\n"
        "E VALORES MOBILIARIOS LTDA 5 R$ 52,28 R$ 261,40\n"
        "05 de novembro de 2026\n"
        "APLICAÇÃO CDB - CDBU2626QQS BANCO INTER S/A 1167 R$ 0,01 R$ 11,67\n"
    )
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = adapt_b3_investor_pdf_to_canonical(b"%PDF-fake-b3-multiline")

    assert result.success is True
    assert len(result.canonical_rows) == 3

    ggrc_row = result.canonical_rows[0]
    assert ggrc_row["ticker"] == "GGRC11"
    assert ggrc_row["asset_type"] == AssetType.FII.value
    assert ggrc_row["operation"] == "buy"
    assert ggrc_row["quantity"] == "10"
    assert ggrc_row["price"] == "8.19"
    assert ggrc_row["date"] == "2026-11-06"

    divd_row = result.canonical_rows[1]
    assert divd_row["ticker"] == "DIVD11"
    assert divd_row["asset_type"] == AssetType.ETF_NACIONAL.value
    assert divd_row["operation"] == "buy"
    assert divd_row["quantity"] == "5"
    assert divd_row["price"] == "52.28"
    assert divd_row["date"] == "2026-11-06"

    cdb_row = result.canonical_rows[2]
    assert cdb_row["ticker"] == "CDB - CDBU2626QQS"
    assert cdb_row["asset_type"] == AssetType.RENDA_FIXA.value
    assert cdb_row["operation"] == "buy"
    assert cdb_row["quantity"] == "1167"
    assert cdb_row["price"] == "0.01"
    assert cdb_row["date"] == "2026-11-05"


@pytest.mark.asyncio
async def test_catalog_reconciliation_in_dry_run():
    db = AsyncMock(spec=AsyncSession)
    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = SimpleNamespace(id=1, user_id=7)
    duplicate_result = MagicMock()
    duplicate_result.scalar_one_or_none.return_value = None

    coverage_result = MagicMock()
    coverage_result.all.return_value = [
        SimpleNamespace(
            ticker="DIVD11",
            asset_type=AssetType.ETF_NACIONAL.value,
            last_price=69.89,
            price_rows=120,
        )
    ]
    duplicate_recheck_result = MagicMock()
    duplicate_recheck_result.scalar_one_or_none.return_value = None

    # portfolio check -> duplicate initial -> coverage preflight (reconciles FII->ETF_NACIONAL) -> duplicate recheck
    db.execute.side_effect = [
        portfolio_result,
        duplicate_result,
        coverage_result,
        duplicate_recheck_result,
    ]

    # Entrada informando FII erroneamente para DIVD11
    csv_bytes = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes\n"
        "DIVD11,FII,buy,10,50.00,2026-05-10,0,BRL,teste\n"
    ).encode("utf-8")

    res = await import_transactions_csv(
        db=db,
        portfolio_id=1,
        user_id=7,
        file=FakeUpload(csv_bytes),
        dry_run=True,
        source="canonical",
    )

    assert res["success"] is True
    assert len(res["rows"]) == 1
    # Auto-reconciliado para ETF_NACIONAL
    assert res["rows"][0]["ticker"] == "DIVD11"
    assert res["rows"][0]["status"] == "valid"


def test_adapt_b3_movimentacao_pdf_wrapped_header():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "06 de novembro de 2026\n"
        "Movimentação Produto\n"
        "Instituição Quantidade Preço Unitário Valor da Operação\n"
        "Venda VALE3 - VALE S.A. INTER DISTRIBUIDORA DE TITULOS 50 R$ 70,00 R$ 3.500,00\n"
    )
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = adapt_b3_investor_pdf_to_canonical(b"%PDF-fake-b3-wrapped-header")

    assert result.success is True
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "VALE3"
    assert result.canonical_rows[0]["operation"] == "sell"
    assert result.canonical_rows[0]["quantity"] == "50"
    assert result.canonical_rows[0]["price"] == "70.00"


@pytest.mark.asyncio
async def test_duplicate_detection_after_reconciliation():
    db = AsyncMock(spec=AsyncSession)
    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = SimpleNamespace(id=1, user_id=7)
    duplicate_initial_result = MagicMock()
    duplicate_initial_result.scalar_one_or_none.return_value = None

    # Cobertura do catálogo tem DIVD11 como ETF_NACIONAL
    coverage_result = MagicMock()
    coverage_result.all.return_value = [
        SimpleNamespace(
            ticker="DIVD11",
            asset_type=AssetType.ETF_NACIONAL.value,
            last_price=69.89,
            price_rows=120,
        )
    ]

    # Já existe uma transação no banco com ETF_NACIONAL
    duplicate_recheck_result = MagicMock()
    duplicate_recheck_result.scalar_one_or_none.return_value = SimpleNamespace(id=99)

    # Execuções: portfolio_result -> duplicate initial (passa com FII) -> coverage_result (reconcilia FII->ETF_NACIONAL) -> duplicate recheck (bloqueia como duplicata com ETF_NACIONAL)
    db.execute.side_effect = [
        portfolio_result,
        duplicate_initial_result,
        coverage_result,
        duplicate_recheck_result,
    ]

    csv_bytes = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes\n"
        "DIVD11,FII,buy,10,50.00,2026-05-10,0,BRL,teste\n"
    ).encode("utf-8")

    res = await import_transactions_csv(
        db=db,
        portfolio_id=1,
        user_id=7,
        file=FakeUpload(csv_bytes),
        dry_run=True,
        source="canonical",
    )

    # Reconciliado para ETF_NACIONAL e então detectado como duplicata existente
    assert res["success"] is False
    assert len(res["rows"]) == 1
    assert "duplicate transaction already exists" in res["rows"][0]["errors"]
