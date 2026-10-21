"""Testes para csv_import_service — importacao de transacoes via CSV."""
import csv
import inspect
import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.asset import Asset, AssetType
from app.models.fixed_income_contract import FixedIncomeContract
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.services import csv_import_service
from app.services.asset_universe_membership_service import (
    CRYPTO_TOP100_UNIVERSE_KEY,
)
from app.services.csv_import_service import (
    CSVRow,
    _parse_date,
    _validate_writer_preflight,
    export_transactions_csv,
    generate_csv_template,
    import_csv_transactions,
    parse_csv_content,
)
from app.services.transaction_write_service import TransactionWriteError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TestGenerateCSVTemplate:

    def test_template_has_all_headers(self):
        template = generate_csv_template()
        assert "ticker" in template
        assert "asset_type" in template
        assert "operation" in template
        assert "quantity" in template
        assert "price" in template
        assert "date" in template
        assert "fees" in template
        assert "currency" in template
        assert "notes" in template
        assert "fixed_income_contract_key" in template
        assert "fixed_income_product_type" in template
        assert "fixed_income_display_name" in template

    def test_template_has_example_rows(self):
        template = generate_csv_template()
        assert "PETR4" in template
        assert "VALE3" in template
        assert "IVVB11" in template
        assert "buy" in template

    def test_template_is_valid_csv(self):
        import csv
        import io
        template = generate_csv_template()
        reader = csv.DictReader(io.StringIO(template))
        rows = list(reader)
        assert len(rows) == 3


def test_import_csv_transactions_uses_canonical_write_boundary():
    source = inspect.getsource(csv_import_service.import_csv_transactions)

    assert "add_transaction_record(" in source
    assert "Transaction(" not in source


@pytest.mark.asyncio
async def test_legacy_fixed_income_csv_remains_unlinked_and_uses_canonical_writer():
    db = AsyncMock(spec=AsyncSession)
    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = SimpleNamespace(user_id=7)
    db.execute.return_value = portfolio_result
    content = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes\n"
        "CDB LEGADO,RENDA_FIXA,buy,1,1000,2026-10-17,0,BRL,Indexador CDI\n"
    )
    transaction = SimpleNamespace(id=91)

    with (
        patch(
            "app.services.csv_import_service._validate_duplicate_transactions",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.csv_import_service._validate_writer_preflight",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.csv_import_service.add_transaction_record",
            new_callable=AsyncMock,
            return_value=transaction,
        ) as writer,
        patch(
            "app.services.csv_import_service.invalidate_portfolio_cache",
            new_callable=AsyncMock,
        ),
    ):
        result = await import_csv_transactions(
            content=content,
            portfolio_id=12,
            user_id=7,
            db=db,
        )

    assert result["success"] is True
    assert result["imported_count"] == 1
    payload = writer.await_args.kwargs["payload"]
    assert payload.asset_type == "RENDA_FIXA"
    assert payload.fixed_income_contract_id is None
    assert payload.fixed_income_contract is None


@pytest.mark.asyncio
async def test_csv_contract_metadata_is_validated_and_grouped_by_file_key():
    content = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes,"
        "fixed_income_contract_key,fixed_income_product_type,fixed_income_display_name,"
        "fixed_income_issuer,fixed_income_indexer,fixed_income_rate_value,"
        "fixed_income_rate_unit,fixed_income_maturity_date,fixed_income_liquidity_type,"
        "fixed_income_grace_period_end,fixed_income_tax_exempt,fixed_income_currency\n"
        "CDB ALPHA,RENDA_FIXA,buy,1,1000,2026-01-10,0,BRL,,ALPHA,CDB,Alpha CDB,"
        "Banco Alpha,CDI,100,PERCENT_OF_INDEXER,2030-12-31,AT_MATURITY,,false,BRL\n"
        "CDB ALPHA,RENDA_FIXA,buy,2,1000,2026-02-10,0,BRL,,ALPHA,CDB,Alpha CDB,"
        "Banco Alpha,CDI,100,PERCENT_OF_INDEXER,2030-12-31,AT_MATURITY,,false,BRL\n"
    )
    rows, global_errors = await parse_csv_content(content, 1, AsyncMock(spec=AsyncSession))

    assert global_errors == []
    assert all(row.is_valid() for row in rows)
    assert rows[0].data["fixed_income_contract_key"] == "ALPHA"
    assert rows[0].data["fixed_income_contract"].display_name == "Alpha CDB"
    assert rows[1].data["fixed_income_contract"].product_type == "CDB"


@pytest.mark.asyncio
async def test_csv_rejects_contract_metadata_for_non_fixed_income_rows():
    content = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes,"
        "fixed_income_contract_key,fixed_income_product_type,fixed_income_display_name\n"
        "PETR4,ACAO,buy,1,10,2026-01-10,0,BRL,,P1,CDB,Alpha CDB\n"
    )
    rows, global_errors = await parse_csv_content(content, 1, AsyncMock(spec=AsyncSession))

    assert global_errors == []
    assert "fixed income contract metadata can only be used with RENDA_FIXA" in rows[0].errors


@pytest.mark.asyncio
async def test_csv_rejects_conflicting_metadata_for_reused_contract_key():
    content = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes,"
        "fixed_income_contract_key,fixed_income_product_type,fixed_income_display_name\n"
        "CDB A,RENDA_FIXA,buy,1,100,2026-01-10,0,BRL,,P1,CDB,Alpha\n"
        "CDB B,RENDA_FIXA,buy,1,100,2026-01-11,0,BRL,,P1,CDB,Beta\n"
    )
    rows, global_errors = await parse_csv_content(content, 1, AsyncMock(spec=AsyncSession))

    assert global_errors == []
    assert rows[0].is_valid()
    assert rows[1].errors == [
        "fixed income contract key 'P1' has inconsistent metadata"
    ]


@pytest.mark.asyncio
async def test_csv_import_export_round_trip_recreates_one_portfolio_scoped_contract(
    db, portfolio
):
    content = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes,"
        "fixed_income_contract_key,fixed_income_product_type,fixed_income_display_name,"
        "fixed_income_issuer,fixed_income_indexer,fixed_income_rate_value,"
        "fixed_income_rate_unit,fixed_income_maturity_date,fixed_income_liquidity_type,"
        "fixed_income_grace_period_end,fixed_income_tax_exempt,fixed_income_currency\n"
        "CDB ALPHA,RENDA_FIXA,buy,1,1000,2026-01-10,0,BRL,aplicacao,ALPHA,CDB,Alpha CDB,"
        "Banco Alpha,CDI,100,PERCENT_OF_INDEXER,2030-12-31,AT_MATURITY,,false,BRL\n"
        "CDB ALPHA,RENDA_FIXA,buy,2,1000,2026-02-10,0,BRL,aporte,ALPHA,CDB,Alpha CDB,"
        "Banco Alpha,CDI,100,PERCENT_OF_INDEXER,2030-12-31,AT_MATURITY,,false,BRL\n"
    )
    with patch(
        "app.services.csv_import_service.invalidate_portfolio_cache",
        new_callable=AsyncMock,
    ):
        imported = await import_csv_transactions(
            content,
            portfolio.id,
            portfolio.user_id,
            db,
        )

    assert imported["success"] is True
    assert imported["imported_count"] == 2
    contract_result = await db.execute(
        select(FixedIncomeContract).where(
            FixedIncomeContract.portfolio_id == portfolio.id
        )
    )
    contracts = contract_result.scalars().all()
    assert len(contracts) == 1

    exported = await export_transactions_csv(db, portfolio.id)
    exported_rows = list(csv.DictReader(io.StringIO(exported)))
    assert len(exported_rows) == 2
    assert {row["fixed_income_contract_key"] for row in exported_rows} == {
        "FIXED_INCOME_CONTRACT_1"
    }
    assert {row["fixed_income_display_name"] for row in exported_rows} == {"Alpha CDB"}

    second_portfolio = Portfolio(
        user_id=portfolio.user_id,
        name="Carteira Importada",
        description="",
    )
    db.add(second_portfolio)
    await db.flush()
    with patch(
        "app.services.csv_import_service.invalidate_portfolio_cache",
        new_callable=AsyncMock,
    ):
        reimported = await import_csv_transactions(
            exported,
            second_portfolio.id,
            portfolio.user_id,
            db,
        )

    assert reimported["success"] is True
    assert reimported["imported_count"] == 2
    new_contract_result = await db.execute(
        select(FixedIncomeContract).where(
            FixedIncomeContract.portfolio_id == second_portfolio.id
        )
    )
    new_contract = new_contract_result.scalar_one()
    new_transactions = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == second_portfolio.id)
    )
    assert {tx.fixed_income_contract_id for tx in new_transactions.scalars()} == {
        new_contract.id
    }


@pytest.mark.asyncio
async def test_writer_preflight_blocks_market_asset_without_persisted_prices():
    row = CSVRow(
        2,
        {
            "ticker": "NVDA",
            "asset_type": "STOCK",
            "operation": "buy",
            "quantity": "1",
            "price": "100",
            "date": "2026-03-03",
            "fees": "0",
            "currency": "USD",
        },
    )
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = []
    db.execute.return_value = result

    await _validate_writer_preflight([row], db)

    assert row.errors == [
        "NVDA STOCK nao elegivel para importacao: ativo nao esta no catalogo persistido"
    ]


@pytest.mark.asyncio
async def test_writer_preflight_allows_market_asset_with_persisted_prices():
    row = CSVRow(
        2,
        {
            "ticker": "PETR4",
            "asset_type": "ACAO",
            "operation": "buy",
            "quantity": "1",
            "price": "30",
            "date": "2026-03-03",
            "fees": "0",
            "currency": "BRL",
        },
    )
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = [
        MagicMock(
            ticker="PETR4",
            asset_type="ACAO",
            last_price=30,
            price_rows=10,
        )
    ]
    db.execute.return_value = result

    await _validate_writer_preflight([row], db)

    assert row.errors == []


class TestCSVRowClass:

    def test_csv_row_initialization(self):
        data = {"ticker": "PETR4", "quantity": "100"}
        row = CSVRow(2, data)
        assert row.row_num == 2
        assert row.data == data
        assert row.errors == []
        assert row.warnings == []

    def test_add_error(self):
        row = CSVRow(2, {})
        row.add_error("Test error")
        assert "Test error" in row.errors

    def test_add_warning(self):
        row = CSVRow(2, {})
        row.add_warning("Test warning")
        assert "Test warning" in row.warnings

    def test_is_valid_no_errors(self):
        row = CSVRow(2, {})
        assert row.is_valid() is True

    def test_is_valid_with_errors(self):
        row = CSVRow(2, {})
        row.add_error("Error")
        assert row.is_valid() is False

    def test_is_valid_with_only_warnings(self):
        row = CSVRow(2, {})
        row.add_warning("Warning")
        assert row.is_valid() is True


class TestParseDate:

    def test_parse_date_iso_format(self):
        result = _parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_date_slash_format(self):
        result = _parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_dash_format(self):
        result = _parse_date("15-01-2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_iso_slash_format(self):
        result = _parse_date("2024/01/15")
        assert result == date(2024, 1, 15)

    def test_parse_date_invalid_format(self):
        with pytest.raises(ValueError):
            _parse_date("invalid-date")

    def test_parse_date_invalid_day(self):
        with pytest.raises(ValueError):
            _parse_date("2024-13-01")


@pytest.mark.asyncio
class TestParseCSVContent:

    async def test_parse_valid_csv(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,Compra inicial
VALE3,ACAO,buy,50,80.00,2024-02-20,5.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(global_errors) == 0
        assert len(rows) == 2
        assert rows[0].is_valid()
        assert rows[1].is_valid()

    async def test_parse_normalizes_common_crypto_names_to_canonical_tickers(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
Bitcoin,CRIPTO,buy,0.01,300000,2026-01-15,0,BRL,
ethereum,CRIPTO,buy,0.10,15000,2026-01-16,0,BRL,
CARDANO,CRIPTO,buy,10,5,2026-01-17,0,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert global_errors == []
        assert [row.data["ticker"] for row in rows] == ["BTC", "ETH", "ADA"]
        assert all(row.is_valid() for row in rows)

    async def test_parse_resolves_treasury_names_to_canonical_catalog_symbols(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
Tesouro Selic 2031,TESOURO_DIRETO,buy,0.01,15000,2026-01-15,0,BRL,"""

        db = AsyncMock(spec=AsyncSession)

        with patch(
            "app.services.csv_import_service.resolve_treasury_symbol",
            new_callable=AsyncMock,
            return_value="tesouro-selic-01032031",
        ) as resolve_symbol:
            rows, global_errors = await parse_csv_content(content, 1, db)

        resolve_symbol.assert_awaited_once_with(db, "Tesouro Selic 2031")
        assert global_errors == []
        assert rows[0].data["ticker"] == "tesouro-selic-01032031"
        assert rows[0].is_valid()

    async def test_parse_rejects_unresolved_treasury_names(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
Tesouro Inventado 2099,TESOURO_DIRETO,buy,0.01,15000,2026-01-15,0,BRL,"""

        db = AsyncMock(spec=AsyncSession)

        with patch(
            "app.services.csv_import_service.resolve_treasury_symbol",
            new_callable=AsyncMock,
            return_value=None,
        ):
            rows, global_errors = await parse_csv_content(content, 1, db)

        assert global_errors == []
        assert rows[0].data["ticker"] == "TESOURO INVENTADO 2099"
        assert rows[0].errors == [
            "ticker de Tesouro Direto nao encontrado no catalogo persistido"
        ]

    async def test_parse_csv_missing_headers(self):
        content = """ticker,quantity,price
PETR4,100,25.50"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(global_errors) > 0
        assert "Missing required headers" in global_errors[0]

    async def test_parse_csv_missing_ticker(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "ticker is required" in rows[0].errors

    async def test_parse_csv_invalid_asset_type(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,INVALID_TYPE,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "asset_type" in rows[0].errors[0]

    async def test_parse_csv_invalid_operation(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,invalid_op,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "operation" in rows[0].errors[0]

    async def test_parse_csv_invalid_quantity(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,invalid,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "quantity" in rows[0].errors[0]

    async def test_parse_csv_zero_quantity(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,0,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "quantity must be positive" in rows[0].errors

    async def test_parse_csv_invalid_price(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,invalid,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "price" in rows[0].errors[0]

    async def test_parse_csv_zero_price(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,0,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "price must be positive" in rows[0].errors

    async def test_parse_csv_invalid_date(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,invalid-date,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "date" in rows[0].errors[0]

    async def test_parse_csv_future_date_warning(self):
        future_date = "2099-12-31"
        content = f"""ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,{future_date},10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "future" in rows[0].warnings[0].lower()

    async def test_parse_csv_negative_fees(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,-10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "fees cannot be negative" in rows[0].errors

    async def test_parse_csv_invalid_fees(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,invalid,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "fees" in rows[0].errors[0]

    async def test_parse_csv_empty_row(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,
,,,,,,,,
VALE3,ACAO,buy,50,80.00,2024-02-20,5.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 3
        assert "Empty row" in rows[1].warnings[0]

    async def test_parse_csv_empty_file(self):
        content = ""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(global_errors) > 0


@pytest.mark.asyncio
class TestImportCSVTransactions:

    async def test_import_valid_transactions(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,Compra inicial"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)

        existing_tx_result = MagicMock()
        existing_tx_result.scalar_one_or_none = MagicMock(return_value=None)

        coverage_result = MagicMock()
        coverage_result.all.return_value = [
            MagicMock(
                ticker="PETR4",
                asset_type="ACAO",
                last_price=25.50,
                price_rows=1,
            )
        ]
        
        asset_result = MagicMock()
        asset_result.scalar_one_or_none = MagicMock(return_value=None)
        
        alias_result = MagicMock()
        alias_result.scalar_one_or_none = MagicMock(return_value=None)

        db.execute = AsyncMock(
            side_effect=[portfolio_result, existing_tx_result, coverage_result, alias_result, asset_result]
        )
        db.commit = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        
        with patch('app.services.csv_import_service.invalidate_portfolio_cache', new_callable=AsyncMock):
            result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is True
        assert result["imported_count"] == 1

    async def test_import_uses_canonical_crypto_ticker_aliases(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
Bitcoin,CRIPTO,buy,0.01,300000,2026-01-15,0,BRL,cripto por nome comum"""

        db = AsyncMock(spec=AsyncSession)

        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1

        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)

        existing_tx_result = MagicMock()
        existing_tx_result.scalar_one_or_none = MagicMock(return_value=None)

        db.execute = AsyncMock(side_effect=[portfolio_result, existing_tx_result])
        db.commit = AsyncMock()

        with (
            patch(
                "app.services.csv_import_service.add_transaction_record",
                new_callable=AsyncMock,
            ) as add_record,
            patch(
                "app.services.csv_import_service.require_catalog_crypto_asset",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.csv_import_service.invalidate_portfolio_cache",
                new_callable=AsyncMock,
            ),
        ):
            add_record.return_value = Transaction()
            result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is True
        assert result["imported_count"] == 1
        payload = add_record.await_args.kwargs["payload"]
        assert payload.ticker == "BTC"
        assert result["rows"][0]["ticker"] == "BTC"

    async def test_dry_run_allows_catalog_crypto_with_incomplete_history(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
BTC,CRIPTO,buy,0.01,300000,2026-01-15,0,BRL,cripto com cobertura incompleta"""

        db = AsyncMock(spec=AsyncSession)

        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1

        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)

        existing_tx_result = MagicMock()
        existing_tx_result.scalar_one_or_none = MagicMock(return_value=None)

        crypto_asset = Asset(
            id=10,
            ticker="BTC",
            asset_type=AssetType.CRIPTO.value,
            provider="brapi",
            provider_status="HISTORY_END_UNAVAILABLE",
        )
        crypto_asset_result = MagicMock()
        crypto_asset_result.scalar_one_or_none = MagicMock(return_value=crypto_asset)

        db.execute = AsyncMock(
            side_effect=[portfolio_result, existing_tx_result, crypto_asset_result]
        )

        result = await csv_import_service.import_transactions_csv(
            db=db,
            portfolio_id=1,
            user_id=1,
            file=MagicMock(read=AsyncMock(return_value=content.encode("utf-8"))),
            dry_run=True,
        )

        assert result["success"] is True
        assert result["imported_count"] == 0
        assert result["error_count"] == 0
        assert result["rows"][0]["status"] == "valid"
        assert result["rows"][0]["errors"] == []

    async def test_import_rolls_back_when_later_canonical_writer_row_fails(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,ok
UNKNOWN,CRIPTO,buy,1,10,2024-01-16,0,BRL,erro"""

        db = AsyncMock(spec=AsyncSession)

        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1

        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)

        first_duplicate_check = MagicMock()
        first_duplicate_check.scalar_one_or_none = MagicMock(return_value=None)
        second_duplicate_check = MagicMock()
        second_duplicate_check.scalar_one_or_none = MagicMock(return_value=None)

        db.execute = AsyncMock(
            side_effect=[
                portfolio_result,
                first_duplicate_check,
                second_duplicate_check,
            ]
        )
        db.commit = AsyncMock()
        db.rollback = AsyncMock()

        with (
            patch(
                "app.services.csv_import_service.add_transaction_record",
                new_callable=AsyncMock,
            ) as add_record,
            patch(
                "app.services.csv_import_service._validate_writer_preflight",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.csv_import_service.invalidate_portfolio_cache",
                new_callable=AsyncMock,
            ) as invalidate,
        ):
            add_record.side_effect = [
                Transaction(),
                TransactionWriteError("cripto invalida"),
            ]
            result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert result["imported_count"] == 0
        assert result["error_count"] == 1
        assert add_record.await_count == 2
        assert result["rows"][0]["status"] == "skipped"
        assert result["rows"][0]["warnings"] == [
            "transaction rolled back because batch has errors"
        ]
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()
        invalidate.assert_not_awaited()

    async def test_import_skips_duplicate_transaction_without_reinserting(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,Compra inicial"""

        db = AsyncMock(spec=AsyncSession)

        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1

        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)

        duplicate_result = MagicMock()
        duplicate_result.scalar_one_or_none = MagicMock(return_value=Transaction())

        db.execute = AsyncMock(side_effect=[portfolio_result, duplicate_result])
        db.add = MagicMock()
        db.commit = AsyncMock()

        with patch('app.services.csv_import_service.invalidate_portfolio_cache', new_callable=AsyncMock) as invalidate:
            result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is True
        assert result["imported_count"] == 0
        assert result["skipped_count"] == 1
        assert result["rows"][0]["status"] == "skipped"
        assert result["rows"][0]["warnings"] == ["duplicate transaction skipped"]
        db.add.assert_not_called()
        db.commit.assert_not_awaited()
        invalidate.assert_not_awaited()

    async def test_import_portfolio_not_found(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert "not found" in result["global_errors"][0].lower()

    async def test_import_unauthorized_user(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 999
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert "Unauthorized" in result["global_errors"][0]

    async def test_import_with_validation_errors(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,invalid,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert result["error_count"] > 0
        db.add.assert_not_called()

    async def test_import_is_atomic_when_any_row_has_error(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,ok
VALE3,ACAO,buy,invalid,80.00,2024-02-20,5.00,BRL,erro"""

        db = AsyncMock(spec=AsyncSession)

        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1

        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)

        db.execute = AsyncMock(return_value=portfolio_result)
        db.add = MagicMock()

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert result["imported_count"] == 0
        assert result["error_count"] == 1
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_import_with_warnings_skipped(self):
        future_date = "2099-12-31"
        content = f"""ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,{future_date},10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert result["imported_count"] == 0
        assert result["skipped_count"] == 1
