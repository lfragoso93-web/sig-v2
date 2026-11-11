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

    # Ordenadas cronologicamente: 2026-11-05 antes de 2026-11-06
    cdb_row = result.canonical_rows[0]
    assert cdb_row["ticker"] == "CDB - CDBU2626QQS"
    assert cdb_row["asset_type"] == AssetType.RENDA_FIXA.value
    assert cdb_row["operation"] == "buy"
    assert cdb_row["quantity"] == "1167"
    assert cdb_row["price"] == "0.01"
    assert cdb_row["date"] == "2026-11-05"

    by_ticker = {r["ticker"]: r for r in result.canonical_rows[1:]}
    ggrc_row = by_ticker["GGRC11"]
    assert ggrc_row["asset_type"] == AssetType.FII.value
    assert ggrc_row["operation"] == "buy"
    assert ggrc_row["quantity"] == "10"
    assert ggrc_row["price"] == "8.19"
    assert ggrc_row["date"] == "2026-11-06"

    divd_row = by_ticker["DIVD11"]
    assert divd_row["asset_type"] == AssetType.ETF_NACIONAL.value
    assert divd_row["operation"] == "buy"
    assert divd_row["quantity"] == "5"
    assert divd_row["price"] == "52.28"
    assert divd_row["date"] == "2026-11-06"


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


def test_subscription_rights_segregated_as_corporate_events():
    from app.services.b3_investor_area_adapter_service import (
        adapt_b3_investor_csv_to_canonical,
        is_subscription_right_ticker,
    )

    assert is_subscription_right_ticker("SNAG12") is True
    assert is_subscription_right_ticker("MXRF12") is True
    assert is_subscription_right_ticker("XPML13") is True
    assert is_subscription_right_ticker("ITSA2") is True
    assert is_subscription_right_ticker("VULC1") is True
    assert is_subscription_right_ticker("PETR4") is False
    assert is_subscription_right_ticker("HGLG11") is False

    # Testa segregação no fluxo tabular B3
    csv_bytes = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Debito;18/03/2026;Transferência - Liquidação;SNAG12 - SUNO AGRO - FIAGRO-IMOBILIARIO;INTER DTVM;80;0,05;4,00\n"
        "Credito;19/03/2026;Transferência - Liquidação;SNAG11 - SUNO AGRO - FIAGRO-IMOBILIARIO;INTER DTVM;10;10,00;100,00\n"
    ).encode("utf-8")

    result = adapt_b3_investor_csv_to_canonical(csv_bytes)
    assert result.success is True
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "SNAG11"
    assert len(result.skipped_items) == 1
    assert "SNAG12" in result.skipped_items[0].raw_ticker
    assert "subscrição" in result.skipped_items[0].reason.lower()


def test_b3_movimentacao_segregates_orphan_fixed_income_resgates_and_sorts_chronologically():
    csv_content = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Debito;06/11/2026;RESGATE ANTECIPADO;CDB - CDB_ORPHAN;BANCO INTER S/A;500;0,01;5,00\n"
        "Debito;05/11/2026;RESGATE ANTECIPADO;CDB - CDB_WITH_BUY;BANCO INTER S/A;1000;0,01;10,00\n"
        "Credito;04/11/2026;APLICAÇÃO;CDB - CDB_WITH_BUY;BANCO INTER S/A;1000;0,01;10,00\n"
        "Credito;03/11/2026;Transferência - Liquidação;PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS;XP;100;30,00;3000,00\n"
    )
    result = adapt_b3_investor_csv_to_canonical(csv_content)
    assert result.success is True
    # CDB_ORPHAN sem aplicação deve ter sido segregado para skipped_items
    assert len(result.skipped_items) == 1
    assert "CDB_ORPHAN" in result.skipped_items[0].raw_ticker
    assert "Resgate de Renda Fixa sem aplicação" in result.skipped_items[0].reason

    # Linhas canônicas devem ter 3 itens ordenados cronologicamente
    assert len(result.canonical_rows) == 3
    dates = [r["date"] for r in result.canonical_rows]
    assert dates == ["2026-11-03", "2026-11-04", "2026-11-05"]
    assert result.canonical_rows[0]["ticker"] == "PETR4"
    assert result.canonical_rows[1]["ticker"] == "CDB - CDB_WITH_BUY"
    assert result.canonical_rows[1]["operation"] == "buy"
    assert result.canonical_rows[2]["ticker"] == "CDB - CDB_WITH_BUY"
    assert result.canonical_rows[2]["operation"] == "sell"


def test_b3_movimentacao_incorporates_custody_events_desdobro_and_atualizacao():
    csv_content = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;28/04/2025;Desdobro;ALZC11 - ALIANZA CREDITO IMOBILIARIO;INTER DTVM;36;0;0\n"
        "Credito;26/11/2025;Atualização;RBRX11 - RBR PLUS MULTIESTRATÉGIA;INTER DTVM;102,52;0;0\n"
        "Debito;27/11/2025;Fração em Ativos;RBRX11 - RBR PLUS MULTIESTRATÉGIA;INTER DTVM;0,52;0;0\n"
        "Credito;19/12/2025;Bonificação em Ativos;KLBN11 - KLABIN S/A;XP;10;0;0\n"
    )
    result = adapt_b3_investor_csv_to_canonical(csv_content)
    assert result.success is True
    assert len(result.canonical_rows) == 4

    # Desdobro ALZC11
    alzc = result.canonical_rows[0]
    assert alzc["ticker"] == "ALZC11"
    assert alzc["operation"] == "buy"
    assert alzc["quantity"] == "36"
    assert alzc["price"] == "0.01"
    assert "Evento Corporativo: Desdobro" in alzc["notes"]

    # Atualização RBRX11 (Credito)
    rbrx_cred = result.canonical_rows[1]
    assert rbrx_cred["ticker"] == "RBRX11"
    assert rbrx_cred["operation"] == "buy"
    assert rbrx_cred["quantity"] == "102.52"
    assert rbrx_cred["price"] == "0.01"
    assert "Evento Corporativo: Atualização" in rbrx_cred["notes"]

    # Fração em Ativos RBRX11 (Debito)
    rbrx_deb = result.canonical_rows[2]
    assert rbrx_deb["ticker"] == "RBRX11"
    assert rbrx_deb["operation"] == "sell"
    assert rbrx_deb["quantity"] == "0.52"
    assert rbrx_deb["price"] == "0.01"

    # Bonificação KLBN11
    klbn = result.canonical_rows[3]
    assert klbn["ticker"] == "KLBN11"
    assert klbn["operation"] == "buy"
    assert klbn["quantity"] == "10"
    assert klbn["price"] == "0.01"


def test_normalize_b3_ticker_tesouro_with_broker_string():
    from app.services.b3_investor_area_adapter_service import normalize_b3_ticker

    assert (
        normalize_b3_ticker("TESOURO EDUCA+ 2026 INTER DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA")
        == "TESOURO EDUCA+ 2026"
    )
    assert (
        normalize_b3_ticker("TESOURO PREFIXADO 2027 INTER DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA")
        == "TESOURO PREFIXADO 2027"
    )
    assert (
        normalize_b3_ticker("TESOURO RENDA+ APOSENTADORIA EXTRA 2065 INTER DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA")
        == "TESOURO RENDA+ APOSENTADORIA EXTRA 2065"
    )
    assert (
        normalize_b3_ticker("TESOURO SELIC 2029 - NTN-B")
        == "TESOURO SELIC 2029"
    )


def test_b3_movimentacao_segregates_orphan_custody_fractions_without_balance():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    csv_content = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;10/01/2026;Transferência - Liquidação;PETR4 - PETROLEO BRASILEIRO;INTER DTVM;100;30;3000\n"
        "Debito;22/01/2026;Fração em Ativos;KLBN3 - KLABIN S/A;INTER DTVM;0,1;0;0\n"
        "Debito;22/01/2026;Fração em Ativos;KLBN4 - KLABIN S/A;INTER DTVM;0,4;0;0\n"
    )
    result = adapt_b3_investor_csv_to_canonical(csv_content)
    assert result.success is True
    # PETR4 é mantido e as frações de KLBN3 e KLBN4 sem saldo prévio são segregadas como skipped_items
    assert len(result.canonical_rows) == 1
    assert result.canonical_rows[0]["ticker"] == "PETR4"
    assert len(result.skipped_items) == 2
    assert any("KLBN3" in s.raw_ticker for s in result.skipped_items)
    assert any("KLBN4" in s.raw_ticker for s in result.skipped_items)


def test_b3_movimentacao_segregates_btc_lending_and_returns():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Compra 20 SANB11 -> Aluguel BTC 20 (saída traço) -> Retorno BTC 20 (retorno cotação) -> Venda real 20
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Debito;05/08/2026;Transferência - Liquidação;SANB11 - BANCO SANTANDER;INTER DTVM;20;28,50;570,00\n"
        "Credito;06/05/2026;Transferência - Liquidação;SANB11 - BANCO SANTANDER;INTER DTVM;20;28,77;575,40\n"
        "Debito;23/04/2026;Transferência - Liquidação;SANB11 - BANCO SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;17/04/2026;Transferência - Liquidação;SANB11 - BANCO SANTANDER;INTER DTVM;20;31,93;638,60\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors
    # Deve conter apenas 2 transações canônicas: Compra 20 em 17/04 e Venda 20 em 05/08
    assert len(res.canonical_rows) == 2
    assert res.canonical_rows[0]["operation"] == "buy"
    assert res.canonical_rows[0]["date"] == "2026-04-17"
    assert float(res.canonical_rows[0]["price"]) == 31.93
    assert res.canonical_rows[1]["operation"] == "sell"
    assert res.canonical_rows[1]["date"] == "2026-08-05"
    assert float(res.canonical_rows[1]["price"]) == 28.50

    # Saída de aluguel e retorno devem ser segregados em skipped_items
    btc_skips = [s for s in res.skipped_items if "BTC" in s.movement_type or "Aluguel" in s.movement_type]
    assert len(btc_skips) == 2


def test_b3_movimentacao_atualizacao_custody_idempotency():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Caso 1: RBRF11 já possui 120 cotas compradas -> Atualização de 120 é idempotente (não duplica) -> Resgate 120 zera
    # Caso 2: RBRX11 possui 0 cotas -> Atualização de 102.52 incorpora delta de 102.52 -> Venda de 100 deixa saldo 2.52
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Debito;10/09/2026;Transferência - Liquidação;RBRX11 - RBR PLUS;INTER DTVM;100;7,21;721,00\n"
        "Credito;26/11/2025;Atualização;RBRX11 - RBR PLUS;INTER DTVM;102,52;-;-\n"
        "Debito;01/12/2025;Resgate;RBRF11 - RBR ALPHA;INTER DTVM;120;0,33;39,60\n"
        "Credito;26/11/2025;Atualização;RBRF11 - RBR ALPHA;INTER DTVM;120;-;-\n"
        "Credito;01/09/2025;Transferência - Liquidação;RBRF11 - RBR ALPHA;INTER DTVM;120;6,54;784,80\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    # RBRF11: compra 120, resgate 120 (Atualização segregada por idempotência)
    rbrf_rows = [r for r in res.canonical_rows if r["ticker"] == "RBRF11"]
    assert len(rbrf_rows) == 2
    assert rbrf_rows[0]["operation"] == "buy" and rbrf_rows[0]["quantity"] == "120"
    assert rbrf_rows[1]["operation"] == "sell" and rbrf_rows[1]["quantity"] == "120"

    # RBRX11: Atualização adiciona delta 102.52, depois venda de 100
    rbrx_rows = [r for r in res.canonical_rows if r["ticker"] == "RBRX11"]
    assert len(rbrx_rows) == 2
    assert rbrx_rows[0]["operation"] == "buy" and rbrx_rows[0]["quantity"] == "102.52"
    assert rbrx_rows[1]["operation"] == "sell" and rbrx_rows[1]["quantity"] == "100"


def test_b3_movimentacao_unpaired_transfers_and_unit_fraction_dismantling():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Simula ciclo real de bonificação e desmonte de fração de Unit (KLBN11 -> KLBN3 + KLBN4)
    # e transferência interna pareada (TAEE11)
    csv_content = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;07/11/2025;Transferência - Liquidação;KLBN11 - KLABIN S/A;INTER DTVM;10;18,53;185,30\n"
        "Credito;19/12/2025;Bonificação em Ativos;KLBN11 - KLABIN S/A;INTER DTVM;0,1;-;-\n"
        "Debito;23/12/2025;Transferência;KLBN11 - KLABIN S/A;INTER DTVM;0,1;-;-\n"
        "Credito;23/12/2025;Transferência;KLBN3 - KLABIN S/A;INTER DTVM;0,1;-;-\n"
        "Credito;23/12/2025;Transferência;KLBN4 - KLABIN S/A;INTER DTVM;0,4;-;-\n"
        "Debito;08/01/2026;Transferência - Liquidação;KLBN11 - KLABIN S/A;INTER DTVM;10;18,70;187,00\n"
        "Debito;22/01/2026;Fração em Ativos;KLBN3 - KLABIN S/A;INTER DTVM;0,1;-;-\n"
        "Debito;22/01/2026;Fração em Ativos;KLBN4 - KLABIN S/A;INTER DTVM;0,4;-;-\n"
        "Débito;15/05/2025;Transferência;TAEE11 - TAESA;INTER DTVM;20;-;-\n"
        "Crédito;15/05/2025;Transferência;TAEE11 - TAESA;INTER DTVM;20;-;-\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_content)
    assert res.success is True, res.errors

    # TAEE11 pareada deve ser segregada
    taee_rows = [r for r in res.canonical_rows if r["ticker"] == "TAEE11"]
    assert len(taee_rows) == 0
    taee_skips = [s for s in res.skipped_items if s.raw_ticker and "TAEE11" in s.raw_ticker]
    assert len(taee_skips) == 2
    assert all("pareada" in s.reason for s in taee_skips)

    # KLBN11: Compra 10 + Bonif 0.1 - Transf 0.1 - Venda 10 = Saldo 0.0
    klbn11_rows = [r for r in res.canonical_rows if r["ticker"] == "KLBN11"]
    assert len(klbn11_rows) == 4
    klbn11_net = sum(
        float(r["quantity"]) if r["operation"] == "buy" else -float(r["quantity"])
        for r in klbn11_rows
    )
    assert round(klbn11_net, 4) == 0.0

    # KLBN3: Transf 0.1 - Fracao 0.1 = Saldo 0.0
    klbn3_rows = [r for r in res.canonical_rows if r["ticker"] == "KLBN3"]
    assert len(klbn3_rows) == 2
    klbn3_net = sum(
        float(r["quantity"]) if r["operation"] == "buy" else -float(r["quantity"])
        for r in klbn3_rows
    )
    assert round(klbn3_net, 4) == 0.0

    # KLBN4: Transf 0.4 - Fracao 0.4 = Saldo 0.0
    klbn4_rows = [r for r in res.canonical_rows if r["ticker"] == "KLBN4"]
    assert len(klbn4_rows) == 2
    klbn4_net = sum(
        float(r["quantity"]) if r["operation"] == "buy" else -float(r["quantity"])
        for r in klbn4_rows
    )
    assert round(klbn4_net, 4) == 0.0

def test_b3_movimentacao_segregates_grupamento_fraction_to_prevent_double_deduction():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Compra 6 NIKE34 -> Grupamento 1.2 (5:1) -> Fração em Ativos 0.2 (saída para leilão)
    # A Fração em Ativos DEVE ser segregada porque o motor corporativo já reduz para 1.0 e isola 0.2 como direito
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Debito;16/10/2026;Fração em Ativos;NIKE34 - NIKE INC;INTER DTVM;0,2;-;-\n"
        "Credito;14/10/2026;Grupamento;NIKE34 - NIKE INC;INTER DTVM;1,2;-;-\n"
        "Credito;05/05/2026;Transferência - Liquidação;NIKE34 - NIKE INC;INTER DTVM;3;22,15;66,45\n"
        "Credito;07/05/2025;Transferência - Liquidação;NIKE34 - NIKE INC;INTER DTVM;2;32,75;65,50\n"
        "Credito;05/02/2025;Transferência - Liquidação;NIKE34 - NIKE INC;INTER DTVM;1;44,50;44,50\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    # Apenas as 3 compras genuínas devem ser geradas (1 + 2 + 3 = 6 ações)
    nike_rows = [r for r in res.canonical_rows if r["ticker"] == "NIKE34"]
    assert len(nike_rows) == 3
    assert all(r["operation"] == "buy" for r in nike_rows)
    assert sum(float(r["quantity"]) for r in nike_rows) == 6.0

    # Grupamento e Fração em Ativos devem constar como segregados
    assert any("Fração em Ativos (Grupamento)" in s.movement_type for s in res.skipped_items)


def test_b3_movimentacao_preserves_genuine_buys_during_active_btc_loan():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Compra 14 ALOS3 -> Aluguel 14 (Debito Transf + Credito Empréstimo)
    # Compra genuína 6 ALOS3 (não deve ser engolida como retorno de aluguel!)
    # Retorno real 14 ALOS3 (Credito Empréstimo sem débito -> Credito Transf Liquidação)
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;26/05/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;14;28,79;403,06\n"
        "Credito;25/05/2026;Empréstimo;ALOS3 - ALLOS S.A;INTER DTVM;14;-;-\n"
        "Credito;06/04/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;6;31,05;186,30\n"
        "Credito;30/03/2026;Empréstimo;ALOS3 - ALLOS S.A;INTER DTVM;14;-;-\n"
        "Debito;30/03/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;14;-;-\n"
        "Credito;26/03/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;14;29,56;413,84\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    # Devem existir 2 compras canônicas: 14 em 26/03 e 6 em 06/04 (total 20 ações)
    alos_buys = [r for r in res.canonical_rows if r["ticker"] == "ALOS3" and r["operation"] == "buy"]
    assert len(alos_buys) == 2
    assert alos_buys[0]["date"] == "2026-03-26" and float(alos_buys[0]["quantity"]) == 14.0
    assert alos_buys[1]["date"] == "2026-04-06" and float(alos_buys[1]["quantity"]) == 6.0

    # Retorno de 14 em 26/05 deve ser segregado como Retorno de Aluguel
    returns = [s for s in res.skipped_items if "Retorno de Aluguel" in s.movement_type]
    assert len(returns) == 1

def test_b3_movimentacao_loan_closure_on_same_day_as_market_sale():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Empréstimo aberto em 10/03 -> Empréstimo encerrado em 25/05 NO MESMO DIA de uma venda a mercado com preço!
    # A venda a mercado não deve anular a evidência do encerramento do BTC em 25/05.
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;26/05/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;14;28,79;403,06\n"
        "Debito;25/05/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;10;29,00;290,00\n"
        "Credito;25/05/2026;Empréstimo;ALOS3 - ALLOS S.A;INTER DTVM;14;-;-\n"
        "Credito;10/03/2026;Empréstimo;ALOS3 - ALLOS S.A;INTER DTVM;14;-;-\n"
        "Debito;10/03/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;14;-;-\n"
        "Credito;05/03/2026;Transferência - Liquidação;ALOS3 - ALLOS S.A.;INTER DTVM;24;30,00;720,00\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    # Apenas 1 compra (24 em 05/03) e 1 venda (10 em 25/05); retorno de 14 em 26/05 deve ser segregado!
    alos_buys = [r for r in res.canonical_rows if r["ticker"] == "ALOS3" and r["operation"] == "buy"]
    alos_sells = [r for r in res.canonical_rows if r["ticker"] == "ALOS3" and r["operation"] == "sell"]
    assert len(alos_buys) == 1 and float(alos_buys[0]["quantity"]) == 24.0
    assert len(alos_sells) == 1 and float(alos_sells[0]["quantity"]) == 10.0
    assert len([s for s in res.skipped_items if "Retorno de Aluguel" in s.movement_type]) == 1


def test_b3_movimentacao_only_segregates_fraction_debit_after_grupamento():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Fração em Ativos ANTERIOR (01/03) de evento prévio não deve ser suprimida pelo Grupamento futuro (14/10).
    # Já a Fração em Ativos posterior (16/10) pertence ao Grupamento e deve ser segregada.
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Debito;16/10/2026;Fração em Ativos;NIKE34 - NIKE INC;INTER DTVM;0,2;-;-\n"
        "Credito;14/10/2026;Grupamento;NIKE34 - NIKE INC;INTER DTVM;1,2;-;-\n"
        "Debito;01/03/2026;Fração em Ativos;NIKE34 - NIKE INC;INTER DTVM;0,5;-;-\n"
        "Credito;01/02/2026;Transferência - Liquidação;NIKE34 - NIKE INC;INTER DTVM;6,5;30,00;195,00\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    # A dedução de 0.5 em 01/03 deve gerar venda técnica (para encerrar a fração prévia), resultando em 6 ações líquidas pré-grupamento
    sells = [r for r in res.canonical_rows if r["ticker"] == "NIKE34" and r["operation"] == "sell"]
    assert len(sells) == 1 and float(sells[0]["quantity"]) == 0.5

    # E somente a fração pós-grupamento (16/10) é segregada como Fração em Ativos (Grupamento)
    grup_skips = [s for s in res.skipped_items if s.movement_type == "Fração em Ativos (Grupamento)"]
    assert len(grup_skips) == 1

def test_b3_movimentacao_mixed_explicit_and_fallback_btc_loans():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Empréstimo legado sem linhas Empréstimo (20 ações) + Empréstimo explícito posterior COM linhas Empréstimo (10 ações)
    # Ambos os retornos devem ser segregados sem engolir compra genuína intermediária!
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;20/06/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;10;30,00;300,00\n"
        "Credito;19/06/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;10;-;-\n"
        "Credito;10/06/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;5;32,00;160,00\n"
        "Credito;01/06/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;10;-;-\n"
        "Debito;01/06/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;10;-;-\n"
        "Credito;20/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;28,00;560,00\n"
        "Debito;10/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;05/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;27,50;550,00\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    # Apenas as 2 compras genuínas devem existir: 20 em 05/02 e 5 em 10/06
    sanb_buys = [r for r in res.canonical_rows if r["ticker"] == "SANB11" and r["operation"] == "buy"]
    assert len(sanb_buys) == 2
    assert float(sanb_buys[0]["quantity"]) == 20.0
    assert float(sanb_buys[1]["quantity"]) == 5.0

    # Ambos os retornos (20 em 20/02 e 10 em 20/06) devem ser segregados como Retorno de Aluguel
    returns = [s for s in res.skipped_items if "Retorno de Aluguel" in s.movement_type]
    assert len(returns) == 2

def test_b3_movimentacao_unbacked_opening_with_explicit_closure_clears_tracker():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Abertura sem linha Empréstimo (20 ações em 10/02) + encerramento explícito COM linha Empréstimo (20 em 20/02)
    # seguida de compra genuína posterior (5 ações em 01/03). A compra genuína NÃO pode ser consumida pelo lent_tracker!
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;01/03/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;5;32,00;160,00\n"
        "Credito;20/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;28,00;560,00\n"
        "Credito;19/02/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Debito;10/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;05/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;27,50;550,00\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    sanb_buys = [r for r in res.canonical_rows if r["ticker"] == "SANB11" and r["operation"] == "buy"]
    assert len(sanb_buys) == 2
    assert float(sanb_buys[0]["quantity"]) == 20.0
    assert float(sanb_buys[1]["quantity"]) == 5.0

def test_b3_movimentacao_paired_opening_without_closure_falls_back_to_lent_tracker():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Compra de 20 SANB11 -> Abertura pareada COM Credito Empréstimo (20) -> Retorno de 20 SEM Empréstimo de fechamento
    # Quando não há nenhum evento Empréstimo de fechamento para o ticker, o retorno de custódia deve ser segregado pelo lent_tracker!
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;20/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;28,00;560,00\n"
        "Credito;10/02/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Debito;10/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;05/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;27,50;550,00\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    sanb_buys = [r for r in res.canonical_rows if r["ticker"] == "SANB11" and r["operation"] == "buy"]
    assert len(sanb_buys) == 1 and float(sanb_buys[0]["quantity"]) == 20.0
    assert len([s for s in res.skipped_items if "Retorno de Aluguel" in s.movement_type]) == 1

def test_b3_movimentacao_duplicate_closure_rows_do_not_consume_later_buy():
    from app.services.b3_investor_area_adapter_service import adapt_b3_investor_csv_to_canonical

    # Duas linhas idênticas de Credito Empréstimo (fechamento duplicado de 20 ações)
    # Após o retorno de 20 ações (saldo alugado zera), uma compra posterior de 5 ações NÃO pode ser descartada pela sobra duplicada!
    csv_descending = (
        "Entrada/Saída;Data;Movimentação;Produto;Instituição;Quantidade;Preço unitário;Valor da Operação\n"
        "Credito;25/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;5;32,00;160,00\n"
        "Credito;20/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;28,00;560,00\n"
        "Credito;19/02/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;19/02/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;10/02/2026;Empréstimo;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Debito;10/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;-;-\n"
        "Credito;05/02/2026;Transferência - Liquidação;SANB11 - SANTANDER;INTER DTVM;20;27,50;550,00\n"
    )
    res = adapt_b3_investor_csv_to_canonical(csv_descending)
    assert res.success is True, res.errors

    sanb_buys = [r for r in res.canonical_rows if r["ticker"] == "SANB11" and r["operation"] == "buy"]
    assert len(sanb_buys) == 2
    assert float(sanb_buys[0]["quantity"]) == 20.0
    assert float(sanb_buys[1]["quantity"]) == 5.0
