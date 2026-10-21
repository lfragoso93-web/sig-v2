"""Testes para o adapter da Área do Investidor B3 (Issue #358)."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.asset import AssetType
from app.services.b3_investor_area_adapter_service import (
    adapt_b3_investor_csv_to_canonical,
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

    # PETR4F deve ter sido normalizado para PETR4
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
